"""Creative generation engine."""

import time
from collections import defaultdict
from typing import Any

from ..models.topic import Topic
from ..models.config import CreativeTypeConfig
from ..models.context import GenerationContext
from ..models.creative import Creative
from ..generators import get_generator_class
from ..clients.llm import LLMClient
from ..clients.gemini import GeminiClient
from ..clients.removebg import RemoveBgClient
from ..clients.creative import CreativeClient


class CreativeEngine:
    """Config-driven creative generation engine."""

    def __init__(
        self,
        llm: LLMClient,
        gemini: GeminiClient,
        removebg: RemoveBgClient,
        creative: CreativeClient,
    ):
        self.llm = llm
        self.gemini = gemini
        self.removebg = removebg
        self.creative = creative

    def generate(
        self,
        topic: Topic,
        config: CreativeTypeConfig,
        inputs: dict[str, Any],
        options: dict[str, Any],
        count: int = 12,
    ) -> list[Creative]:
        """Generate creatives using config-driven approach."""
        # 1. Resolve all sources (generators)
        source_results = self._resolve_sources(topic, config, inputs, options, count)

        # 2. Build and submit Placid jobs for each creative
        creatives = self._build_creatives(config, source_results, inputs, count)

        return creatives

    def _resolve_sources(
        self,
        topic: Topic,
        config: CreativeTypeConfig,
        inputs: dict[str, Any],
        options: dict[str, Any],
        count: int,
    ) -> dict[str, Any]:
        """Resolve all sources (generators and style_pool) to values.

        For batch_creatives=True: returns list of N values (one per creative)
        For batch_creatives=False: returns dict keyed by slot.name (one value per slot)
        """
        results: dict[str, Any] = {}

        # Group slots by source
        slots_by_source: dict[str, list] = defaultdict(list)
        for slot in config.slots:
            slots_by_source[slot.source].append(slot)

        for source, slots in slots_by_source.items():
            if source.startswith("style."):
                # Style sources always return list (one per creative)
                results[source] = self._resolve_style_source(source, config, count)
                continue

            if source.startswith("cta."):
                # CTA sources always return list (one per creative)
                results[source] = self._resolve_cta_source(source, config, count)
                continue

            generator = self._create_generator(source)
            batch_creatives = any(s.batch_creatives for s in slots)

            if batch_creatives:
                # 1 call, count=creative_count → list of N values
                merged_inputs = {**inputs}
                for slot in slots:
                    if slot.generator_config:
                        merged_inputs.update(slot.generator_config)

                context = GenerationContext(
                    topic=topic,
                    inputs=merged_inputs,
                    options=options,
                    count=count,
                )
                results[source] = generator.generate(context)
            else:
                # 1 call per slot, count=1 → dict keyed by slot.name
                results[source] = {}
                for slot in slots:
                    merged_inputs = {**inputs}
                    if slot.generator_config:
                        merged_inputs.update(slot.generator_config)

                    context = GenerationContext(
                        topic=topic,
                        inputs=merged_inputs,
                        options=options,
                        count=1,
                    )
                    value_list = generator.generate(context)
                    results[source][slot.name] = value_list[0]

        return results

    def _resolve_style_source(
        self, source: str, config: CreativeTypeConfig, count: int
    ) -> list[Any]:
        """Resolve style.* source from config.style_pool."""
        if not config.style_pool:
            raise ValueError(f"No style_pool defined for source: {source}")

        # source = "style.background_color" → field = "background_color"
        field = source.split(".", 1)[1]

        # Extract field from each style dict, cycling if needed
        values = [style[field] for style in config.style_pool]
        # Extend to count if style_pool is shorter
        return [values[i % len(values)] for i in range(count)]

    def _resolve_cta_source(
        self, source: str, config: CreativeTypeConfig, count: int
    ) -> list[Any]:
        """Resolve cta.* source from config.cta_pool."""
        if not config.cta_pool:
            raise ValueError(f"No cta_pool defined for source: {source}")

        # source = "cta.button_image" → field = "button_image"
        field = source.split(".", 1)[1]

        # Extract field from each cta dict, cycling if needed
        values = [cta[field] for cta in config.cta_pool]
        # Extend to count if cta_pool is shorter
        return [values[i % len(values)] for i in range(count)]

    def _create_generator(self, source: str):
        """Create generator instance with appropriate clients."""
        generator_class = get_generator_class(source)

        # Inject clients based on generator type
        if source.startswith("text."):
            return generator_class(llm=self.llm)
        elif source.startswith("image."):
            return generator_class(
                gemini=self.gemini,
                removebg=self.removebg,
                creative=self.creative,
            )
        else:
            return generator_class()

    def _build_creatives(
        self,
        config: CreativeTypeConfig,
        source_results: dict[str, Any],
        inputs: dict[str, Any],
        count: int,
    ) -> list[Creative]:
        """Build creatives by submitting Placid jobs."""
        creatives = []
        job_ids = []

        # Submit all jobs first (parallel processing on Placid side)
        for i in range(count):
            # Get variant for this creative
            if config.variant_sequence:
                variant = config.variant_sequence[i]
            else:
                variant = list(config.variants.keys())[0]  # first/only
            variant_uuid = config.variants[variant]

            layers = self._build_layers(config, source_results, inputs, i)
            print(f"[DEBUG] Creative {i} layers: {layers}", flush=True)
            job_id = self.creative.submit_generic_job(variant_uuid, layers)
            job_ids.append((job_id, layers, variant))

        # Poll for results
        for job_id, layers, variant in job_ids:
            creative_url = self._poll_job(job_id)
            creative = Creative(
                creative_type=config.name,
                variant=variant,
                layers=layers,
                creative_url=creative_url,
            )
            creatives.append(creative)

        return creatives

    def _build_layers(
        self,
        config: CreativeTypeConfig,
        source_results: dict[str, Any],
        inputs: dict[str, Any],
        creative_idx: int,
    ) -> dict[str, dict[str, Any]]:
        """Build Placid layers dict from slots.

        For batch_creatives=True or style.*: index by creative_idx into list
        For batch_creatives=False: key by slot.name into dict
        """
        layers: dict[str, dict[str, Any]] = {}

        for slot in config.slots:
            # Check if slot is toggled off (optional slots can be excluded)
            if slot.optional:
                toggle_name = f"include_{slot.name.split('.')[0]}"  # "header.text" -> "include_header"
                if not inputs.get(toggle_name, True):  # Default to included
                    continue  # Skip this slot

            results = source_results[slot.source]

            if slot.batch_creatives or slot.source.startswith("style.") or slot.source.startswith("cta."):
                # Indexed by creative (list of N values)
                value = results[creative_idx]
            else:
                # Keyed by slot name (dict, same for all creatives)
                value = results[slot.name]

            # Parse slot name and build layer
            layer_name, prop_name = slot.name.split(".")
            if layer_name not in layers:
                layers[layer_name] = {}
            layers[layer_name][prop_name] = value

        return layers

    def _poll_job(self, job_id: int, max_attempts: int = 60) -> str:
        """Poll Placid job until complete, return creative_url."""
        for _ in range(max_attempts):
            status, creative_url, error = self.creative.poll_job(job_id)
            if status == "finished" and creative_url:
                return creative_url
            if status == "error":
                raise RuntimeError(f"Placid job failed: {error}")
            time.sleep(1)
        raise RuntimeError("Placid job timed out")

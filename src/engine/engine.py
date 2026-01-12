"""Creative generation engine."""

import time
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
    ) -> dict[str, list[Any]]:
        """Resolve all sources (generators and style_pool) to lists of values."""
        results: dict[str, list[Any]] = {}

        # Find unique sources and their configs
        sources = set()
        generator_configs = {}  # source -> generator_config
        for slot in config.slots:
            sources.add(slot.source)
            if slot.generator_config:
                generator_configs[slot.source] = slot.generator_config

        # Resolve each source
        for source in sources:
            if source.startswith("style."):
                # Handle style sources from style_pool
                results[source] = self._resolve_style_source(source, config)
            else:
                # Handle generator sources
                merged_inputs = {**inputs}
                if source in generator_configs:
                    merged_inputs.update(generator_configs[source])

                context = GenerationContext(
                    topic=topic,
                    inputs=merged_inputs,
                    options=options,
                    count=count,
                )

                generator = self._create_generator(source)
                results[source] = generator.generate(context)

        return results

    def _resolve_style_source(
        self, source: str, config: CreativeTypeConfig
    ) -> list[Any]:
        """Resolve style.* source from config.style_pool."""
        if not config.style_pool:
            raise ValueError(f"No style_pool defined for source: {source}")

        # source = "style.background_color" → field = "background_color"
        field = source.split(".", 1)[1]

        # Extract field from each style dict
        return [style[field] for style in config.style_pool]

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
        source_results: dict[str, list[Any]],
        inputs: dict[str, Any],
        count: int,
    ) -> list[Creative]:
        """Build creatives by submitting Placid jobs."""
        creatives = []
        job_ids = []

        # Pre-compute slot indices for smart distribution
        slot_indices = self._compute_slot_indices(config)

        # Submit all jobs first (parallel processing on Placid side)
        for i in range(count):
            # Get variant for this creative
            if config.variant_sequence:
                variant = config.variant_sequence[i]
            else:
                variant = list(config.variants.keys())[0]  # first/only
            variant_uuid = config.variants[variant]

            layers = self._build_layers(config, source_results, inputs, i, slot_indices)
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

    def _compute_slot_indices(
        self, config: CreativeTypeConfig
    ) -> dict[str, dict[str, Any]]:
        """Compute slot indices for each source (for smart distribution)."""
        slot_indices: dict[str, dict[str, Any]] = {}

        for slot in config.slots:
            source = slot.source
            if source not in slot_indices:
                slot_indices[source] = {"count": 0, "slots": {}}

            # Assign index to this slot for its source
            slot_indices[source]["slots"][slot.name] = slot_indices[source]["count"]
            slot_indices[source]["count"] += 1

        return slot_indices

    def _build_layers(
        self,
        config: CreativeTypeConfig,
        source_results: dict[str, list[Any]],
        inputs: dict[str, Any],
        index: int,
        slot_indices: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Build Placid layers dict from slots."""
        layers: dict[str, dict[str, Any]] = {}

        for slot in config.slots:
            # Check if slot is toggled off (optional slots can be excluded)
            if slot.optional:
                toggle_name = f"include_{slot.name.split('.')[0]}"  # "header.text" -> "include_header"
                if not inputs.get(toggle_name, True):  # Default to included
                    continue  # Skip this slot

            # Smart indexing: distributes across slots first, then creatives
            # Formula: (creative_index * num_slots + slot_idx) % len(results)
            results = source_results[slot.source]
            num_slots = slot_indices[slot.source]["count"]
            slot_idx = slot_indices[slot.source]["slots"][slot.name]
            result_index = (index * num_slots + slot_idx) % len(results)
            value = results[result_index]

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

"""3-stage text generation pipeline orchestrator."""

from openai import OpenAI

from .models import GenerationInput, TextVariation, PipelineResult
from .stages import StageExecutor
from .tsv_parser import TSVParser, TSVParseError


class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass


class TextGenerationPipeline:
    """
    Orchestrate 3-stage text generation: CREATOR -> EDITOR -> FINAL TOUCHER.

    Each stage:
    1. CREATOR: Generates 9 initial text variations
    2. EDITOR: Refines and enforces rules
    3. FINAL TOUCHER: Final micro-polish

    Output: 9 TextVariation objects with batch/color assignments.
    """

    def __init__(self, openai_api_key: str, model: str = "gpt-5.1"):
        self.client = OpenAI(api_key=openai_api_key)
        self.executor = StageExecutor(self.client, model)

    def run(self, input_data: GenerationInput, max_retries: int = 2) -> PipelineResult:
        """
        Execute all 3 stages and return final results.

        Args:
            input_data: Generation parameters (topic, event mode, etc.)
            max_retries: Max retries per stage on TSV parse failure.

        Returns:
            PipelineResult with 9 TextVariations and raw outputs.

        Raises:
            PipelineError: If any stage fails after retries.
        """
        # Stage 1: CREATOR
        print("=== STAGE 1: CREATOR ===", flush=True)
        creator_output = self._run_stage_with_retry(
            stage_name="CREATOR",
            run_fn=lambda: self.executor.run_creator(input_data),
            input_data=input_data,
            max_retries=max_retries,
        )
        creator_rows = TSVParser.parse(creator_output)
        creator_tsv = TSVParser.format_for_next_stage(input_data.topic, creator_rows)

        # Stage 2: EDITOR
        print("=== STAGE 2: EDITOR ===", flush=True)
        editor_output = self._run_stage_with_retry(
            stage_name="EDITOR",
            run_fn=lambda: self.executor.run_editor(input_data, creator_tsv),
            input_data=input_data,
            max_retries=max_retries,
        )
        editor_rows = TSVParser.parse(editor_output)
        editor_tsv = TSVParser.format_for_next_stage(input_data.topic, editor_rows)

        # Stage 3: FINAL TOUCHER
        print("=== STAGE 3: FINAL TOUCHER ===", flush=True)
        final_output = self._run_stage_with_retry(
            stage_name="FINAL_TOUCHER",
            run_fn=lambda: self.executor.run_final_toucher(input_data, editor_tsv),
            input_data=input_data,
            max_retries=max_retries,
        )
        final_rows = TSVParser.parse(final_output)

        # Map to TextVariation with color assignments
        variations = [
            TextVariation.from_index(row.index, row.text)
            for row in final_rows
        ]

        return PipelineResult(
            variations=variations,
            raw_creator_output=creator_output,
            raw_editor_output=editor_output,
            raw_final_output=final_output,
        )

    def _run_stage_with_retry(
        self,
        stage_name: str,
        run_fn: callable,
        input_data: GenerationInput,
        max_retries: int,
    ) -> str:
        """Run a stage with retry on TSV parse failure."""
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                output = run_fn()
                # Validate it parses correctly
                TSVParser.parse(output)
                return output
            except TSVParseError as e:
                last_error = e
                if attempt < max_retries:
                    print(
                        f"  {stage_name} attempt {attempt + 1} failed: {e}. Retrying...",
                        flush=True
                    )
                continue

        raise PipelineError(
            f"{stage_name} failed after {max_retries + 1} attempts: {last_error}"
        )

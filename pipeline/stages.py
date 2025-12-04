"""Execute individual pipeline stages."""

from openai import OpenAI

from .models import GenerationInput
from .prompt_loader import PromptLoader
from .tsv_parser import TSVParser


class StageExecutor:
    """Execute a single pipeline stage via OpenAI."""

    def __init__(self, client: OpenAI, model: str = "gpt-5.1"):
        self.client = client
        self.model = model
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def _call_openai(self, system_prompt: str, user_message: str, stage_name: str) -> str:
        """Make OpenAI API call and return response content."""
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "developer", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            reasoning={"effort": "medium"},
        )

        # Track tokens
        usage = response.usage
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        print(f"  {stage_name}: input={input_tokens}, output={output_tokens}", flush=True)

        return response.output_text.strip()

    def run_creator(self, input_data: GenerationInput) -> str:
        """
        Stage 1: CREATOR - Generate initial 12 variations.

        Returns raw output (TSV format).
        """
        system_prompt = PromptLoader.creator()
        user_message = f"{input_data.to_user_message()}\nPlease generate 12 TSV lines."
        return self._call_openai(system_prompt, user_message, "CREATOR")

    def run_editor(self, input_data: GenerationInput, tsv_block: str) -> str:
        """
        Stage 2: EDITOR - Refine the 12 variations.

        Args:
            input_data: Original generation input.
            tsv_block: Formatted TSV from creator stage.

        Returns raw output (TSV format).
        """
        system_prompt = PromptLoader.editor()
        user_message = f"{input_data.to_user_message()}\n\n{tsv_block}"
        return self._call_openai(system_prompt, user_message, "EDITOR")

    def run_final_toucher(self, input_data: GenerationInput, tsv_block: str) -> str:
        """
        Stage 3: FINAL TOUCHER - Final polish on the 12 variations.

        Args:
            input_data: Original generation input.
            tsv_block: Formatted TSV from editor stage.

        Returns raw output (TSV format).
        """
        system_prompt = PromptLoader.final_toucher()
        user_message = f"{input_data.to_user_message()}\n\n{tsv_block}"
        return self._call_openai(system_prompt, user_message, "FINAL_TOUCHER")

    def get_token_totals(self) -> tuple[int, int]:
        """Return (total_input_tokens, total_output_tokens)."""
        return self.total_input_tokens, self.total_output_tokens

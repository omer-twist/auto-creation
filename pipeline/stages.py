"""Execute individual pipeline stages."""

from openai import OpenAI

from .models import GenerationInput
from .prompt_loader import PromptLoader
from .tsv_parser import TSVParser, TSVRow


class StageExecutor:
    """Execute a single pipeline stage via OpenAI."""

    def __init__(self, client: OpenAI, model: str = "gpt-5.1"):
        self.client = client
        self.model = model

    def _call_openai(self, system_prompt: str, user_message: str) -> str:
        """Make OpenAI API call and return response content."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_completion_tokens=2000,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    def run_creator(self, input_data: GenerationInput) -> str:
        """
        Stage 1: CREATOR - Generate initial 9 variations.

        Returns raw output (TSV format).
        """
        system_prompt = PromptLoader.creator()
        user_message = f"{input_data.to_user_message()}\nPlease generate 9 TSV lines."
        return self._call_openai(system_prompt, user_message)

    def run_editor(self, input_data: GenerationInput, tsv_block: str) -> str:
        """
        Stage 2: EDITOR - Refine the 9 variations.

        Args:
            input_data: Original generation input.
            tsv_block: Formatted TSV from creator stage.

        Returns raw output (TSV format).
        """
        system_prompt = PromptLoader.editor()
        user_message = f"{input_data.to_user_message()}\n\n{tsv_block}"
        return self._call_openai(system_prompt, user_message)

    def run_final_toucher(self, input_data: GenerationInput, tsv_block: str) -> str:
        """
        Stage 3: FINAL TOUCHER - Final polish on the 9 variations.

        Args:
            input_data: Original generation input.
            tsv_block: Formatted TSV from editor stage.

        Returns raw output (TSV format).
        """
        system_prompt = PromptLoader.final_toucher()
        user_message = f"{input_data.to_user_message()}\n\n{tsv_block}"
        return self._call_openai(system_prompt, user_message)

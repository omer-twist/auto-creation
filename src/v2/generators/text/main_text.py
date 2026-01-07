"""Main text generator."""

from pathlib import Path

from ..base import Generator
from .. import register
from ...models.context import GenerationContext
from src.clients.llm import LLMClient


@register("text.main_text")
class MainTextGenerator(Generator):
    """Generates main text lines for creatives."""

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm
        self.prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        prompt_path = Path(__file__).parents[2] / "prompts" / "main_text.txt"
        return prompt_path.read_text()

    def generate(self, context: GenerationContext) -> list[str]:
        """
        Generate main text lines.

        If main_lines provided in inputs, use those directly.
        Otherwise, call LLM to generate main texts.
        """
        # Check for override
        if main_lines := context.inputs.get("main_lines"):
            return list(main_lines[:context.count])

        # Generate via LLM
        return self._generate_via_llm(context)

    def _generate_via_llm(self, context: GenerationContext) -> list[str]:
        """Call LLM with single prompt, parse output."""
        if self.llm is None:
            raise ValueError("LLM client required for generation")
        user_message = self._build_user_message(context)
        output = self.llm.call(self.prompt, user_message, label="MAIN_TEXT")
        return self._parse_output(output, context.count)

    def _build_user_message(self, context: GenerationContext) -> str:
        """Build user message with topic info."""
        return f"Topic: {context.topic.name}\n\nGenerate {context.count} main text lines."

    def _parse_output(self, output: str, count: int) -> list[str]:
        """Parse TSV output into list of main texts."""
        lines = []
        for line in output.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('Variation'):
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                lines.append(parts[1].strip())
        return lines[:count]

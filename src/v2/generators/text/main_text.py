"""Main text generator - generates (header, main_text) pairs."""

from pathlib import Path

from ..base import Generator, GeneratorOption
from .. import register
from ...models.context import GenerationContext
from src.clients.llm import LLMClient


def generate_header(topic_name: str) -> str:
    """Header is always the topic name uppercased."""
    return topic_name.upper()


@register("text/main_text")
class MainTextGenerator(Generator):
    """Generates (header, main_text) pairs for creatives."""

    OPTIONS = [
        GeneratorOption(
            name="include_header",
            type="toggle",
            label="Include Header",
            default=True,
        ),
    ]

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm
        self.prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        prompt_path = Path(__file__).parents[2] / "prompts" / "main_text.txt"
        return prompt_path.read_text()

    def generate(self, context: GenerationContext) -> list[tuple[str, str]]:
        """
        Generate (header, main_text) pairs.

        If main_lines provided in inputs, use those directly.
        Otherwise, call LLM to generate main texts.
        """
        header = generate_header(context.topic.name)

        # Check for override
        if main_lines := context.inputs.get("main_lines"):
            return [(header, line) for line in main_lines[:context.count]]

        # Generate via LLM
        main_texts = self._generate_via_llm(context)
        return [(header, text) for text in main_texts]

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

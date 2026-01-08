"""Header text generator."""

from .. import register
from ..base import Generator, GeneratorOption
from ...models.context import GenerationContext
from src.clients.llm import LLMClient


@register("text.header")
class HeaderGenerator(Generator):
    """Generates header text (topic name uppercased)."""

    def __init__(self, llm: LLMClient | None = None):
        # Accept llm for interface consistency, but don't use it
        pass

    OPTIONS = [
        GeneratorOption(
            name="include_header",
            type="toggle",
            label="Include Header",
            default=True,
        ),
    ]

    def generate(self, context: GenerationContext) -> list[str]:
        """Return header text for each creative."""
        header = context.topic.name.upper()
        return [header] * context.count

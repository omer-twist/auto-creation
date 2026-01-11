"""Header text generator."""

from .. import register
from ..base import Generator
from ...models.context import GenerationContext
from ...clients.llm import LLMClient


@register("text.header")
class HeaderGenerator(Generator):
    """Generates header text (topic name uppercased)."""

    # No INPUTS - header text comes from context.topic.name
    # include_header toggle is created from slot.optional

    def __init__(self, llm: LLMClient | None = None):
        # Accept llm for interface consistency, but don't use it
        pass

    def generate(self, context: GenerationContext) -> list[str]:
        """Return header text for each creative."""
        header = context.topic.name.upper()
        return [header] * context.count

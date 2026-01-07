"""Header text generator."""

from .. import register
from ..base import Generator, GeneratorOption
from ...models.context import GenerationContext


@register("text.header")
class HeaderGenerator(Generator):
    """Generates header text (topic name uppercased)."""

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

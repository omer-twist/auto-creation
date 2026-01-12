"""Generator inputs registry - lightweight, no heavy imports."""

from ..models.config import Field

# Maps generator source path to its required inputs
# This is separate from generator classes to avoid importing heavy dependencies (Gemini, OpenAI, etc.)
GENERATOR_INPUTS: dict[str, list[Field]] = {
    "image.cluster": [
        Field(
            name="product_image_urls",
            type="list",
            label="Product Image URLs",
            required=True,
        ),
        Field(
            name="is_people_mode",
            type="toggle",
            label="People Mode",
            default=False,
        ),
    ],
    "text.main_text": [
        Field(
            name="main_lines",
            type="textarea",
            label="Main Text Lines",
            required=False,
        ),
    ],
}


def get_generator_inputs(source: str) -> list[Field]:
    """Get inputs for a generator by source path."""
    return GENERATOR_INPUTS.get(source, [])

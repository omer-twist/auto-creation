"""Creative model."""

from dataclasses import dataclass


@dataclass
class Creative:
    """A generated creative with text and image."""

    text: str
    image_url: str
    background_color: str
    text_color: str
    font: str
    # Product cluster fields (optional)
    text_secondary: str | None = None
    text_color_secondary: str | None = None
    product_image_url: str | None = None

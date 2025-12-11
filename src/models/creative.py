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

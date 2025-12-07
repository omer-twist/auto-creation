"""Style configuration for creatives."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Style:
    """Visual style for a creative."""

    background_color: str
    text_color: str
    font: str


# 12 style combinations (4 batches x 3 colors)
STYLES: list[Style] = [
    # Batch 1
    Style("#3B027A", "#FFFFFF", "exo-extrabold"),  # Purple
    Style("#E20072", "#FFFFFF", "exo-extrabold"),  # Magenta
    Style("#FF5370", "#FFFFFF", "exo-extrabold"),  # Coral
    # Batch 2
    Style("#384152", "#FFFFFF", "exo-extrabold"),  # Dark Gray
    Style("#FF8A00", "#000000", "exo-extrabold"),  # Orange
    Style("#13A4FB", "#000000", "exo-extrabold"),  # Blue
    # Batch 3
    Style("#13A4FB", "#FFFFFF", "exo-extrabold"),  # Blue
    Style("#FFD64F", "#000000", "exo-extrabold"),  # Yellow
    Style("#244168", "#FFFFFF", "exo-extrabold"),  # Navy
    # Batch 4
    Style("#E2A9F1", "#FFFFFF", "exo-extrabold"),  # Lavender Pink
    Style("#004AAD", "#FFFFFF", "exo-extrabold"),  # Deep Blue
    Style("#F49999", "#FFFFFF", "exo-extrabold"),  # Salmon
]


def get_styles() -> list[Style]:
    """Get all 12 style combinations."""
    return STYLES

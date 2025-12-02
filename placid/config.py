from dataclasses import dataclass

from config import (
    PLACID_API_TOKEN as API_TOKEN,
    PLACID_TEMPLATE_UUID as TEMPLATE_UUID,
    OPENAI_API_KEY,
    MONDAY_API_KEY,
    MONDAY_BOARD_ID,
)


@dataclass(frozen=True)
class ColorScheme:
    background_color: str
    text_color: str  # "#FFFFFF" or "#000000"


@dataclass(frozen=True)
class FontConfig:
    name: str


@dataclass(frozen=True)
class ImageVariant:
    """A unique combination to generate"""
    color_scheme: ColorScheme
    font: FontConfig


# Batch-based color configuration - each batch has 3 colors
COLOR_BATCHES: dict[int, list[ColorScheme]] = {
    1: [
        ColorScheme("#3B027A", "#FFFFFF"),  # Purple - White
        ColorScheme("#E20072", "#FFFFFF"),  # Magenta - White
        ColorScheme("#FF5370", "#FFFFFF"),  # Coral - White
    ],
    2: [
        ColorScheme("#384152", "#FFFFFF"),  # Dark Gray - White
        ColorScheme("#FF8A00", "#000000"),  # Orange - Black
        ColorScheme("#13A4FB", "#000000"),  # Blue - Black
    ],
    3: [
        ColorScheme("#13A4FB", "#FFFFFF"),  # Blue - White
        ColorScheme("#FFD64F", "#000000"),  # Yellow - Black
        ColorScheme("#244168", "#FFFFFF"),  # Navy - White
    ],
}

FONTS = [
    FontConfig("exo-extrabold"),
]


def get_variants_for_batch(batch_num: int) -> list[ImageVariant]:
    """Get all color+font combinations for a specific batch."""
    if batch_num not in COLOR_BATCHES:
        raise ValueError(f"Invalid batch_num: {batch_num}. Valid: {list(COLOR_BATCHES.keys())}")

    return [
        ImageVariant(color, font)
        for color in COLOR_BATCHES[batch_num]
        for font in FONTS
    ]


def get_all_variants() -> list[ImageVariant]:
    """Generate all variants across all batches (for testing)."""
    all_colors = []
    for colors in COLOR_BATCHES.values():
        all_colors.extend(colors)
    return [
        ImageVariant(color, font)
        for color in all_colors
        for font in FONTS
    ]


def get_variant_by_index(batch_num: int, color_index: int) -> ImageVariant:
    """
    Get a specific variant by batch number and color index.

    Args:
        batch_num: Batch number (1, 2, or 3)
        color_index: Color index within batch (0, 1, or 2)

    Returns:
        ImageVariant with the specified color and default font.
    """
    if batch_num not in COLOR_BATCHES:
        raise ValueError(f"Invalid batch_num: {batch_num}. Valid: {list(COLOR_BATCHES.keys())}")

    colors = COLOR_BATCHES[batch_num]
    if not 0 <= color_index < len(colors):
        raise ValueError(f"Invalid color_index: {color_index}. Valid: 0-{len(colors)-1}")

    return ImageVariant(colors[color_index], FONTS[0])

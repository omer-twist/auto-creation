import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("PLACID_API_TOKEN")
TEMPLATE_UUID = os.getenv("PLACID_TEMPLATE_UUID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
MONDAY_BOARD_ID = os.getenv("MONDAY_BOARD_ID")


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

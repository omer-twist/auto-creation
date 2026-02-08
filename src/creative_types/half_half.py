"""Half-half creative type configuration."""

from ..models.config import CreativeTypeConfig
from ..models.slot import Slot

# (bg_left, bg_right, text_color, cta_url)
_VARIANTS = [
    (
        "#ebd4f1", "#dfd2d2", "#5F5151",
        "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%238994B2/black.png",
    ),
    (
        "#b8c2dd", "#dfd2d2", "#5F5151",
        "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23004AAD/black.png",
    ),
    (
        "#cba29c", "#dfd2d2", "#5F5151",
        "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23691A1E/white.png",
    ),
    (
        "#626686", "#d9d9d9", "#FFFFFF",
        "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23A6A6A6/white.png",
    ),
]


def _build_style_pool():
    pool = []
    for bg_left, bg_right, text_color, _ in _VARIANTS:
        entry = {"bg_left": bg_left, "bg_right": bg_right, "text_color": text_color}
        pool.extend([entry] * 3)
    return pool


def _build_cta_pool():
    pool = []
    for _, _, _, cta_url in _VARIANTS:
        entry = {"button_image": cta_url}
        pool.extend([entry] * 3)
    return pool


HALF_HALF_CONFIG = CreativeTypeConfig(
    name="half_half",
    display_name="Half Half",
    variants={"default": "iiuu1uj0yzwbk"},
    variant_sequence=["default"] * 12,
    style_pool=_build_style_pool(),
    cta_pool=_build_cta_pool(),
    slots=[
        # Main text - varies per creative
        Slot(name="main_text.text", source="text.main_text", batch_creatives=True),
        # Text color - varies per color variant
        Slot(name="main_text.text_color", source="style.text_color"),
        # Background colors
        Slot(name="bg_left.background_color", source="style.bg_left"),
        Slot(name="bg_right.background_color", source="style.bg_right"),
        # CTA button
        Slot(name="cta.image", source="cta.button_image"),
        # Product image - single image broadcast to all 12
        Slot(name="image.image", source="image.product", generator_config={"input_index": 0, "aspect_ratio": "9:16"}),
    ],
)

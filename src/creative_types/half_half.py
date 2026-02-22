"""Half-half creative type configuration."""

from ..models.config import CreativeTypeConfig
from ..models.slot import Slot

_S3 = "https://creatives-dealogic-assets.s3.amazonaws.com/cta"

# (bg_left, bg_right, text_color, cta_url) — 12 unique variants
_VARIANTS = [
    ("#DA8C90", "#D4D2D6", "#FFFFFF", f"{_S3}/%238994B2/black.png"),
    ("#827171", "#DEE3EF", "#FFFFFF", f"{_S3}/%23FDEDD4/black.png"),
    ("#855E89", "#DEE3EF", "#FFFFFF", f"{_S3}/%23FDEDD4/black.png"),
    ("#B5D7E6", "#ECEFF8", "#000000", f"{_S3}/%23004AAD/black.png"),
    ("#827171", "#FDEDD4", "#FFFFFF", f"{_S3}/%23FDEDD4/black.png"),
    ("#DBD4FD", "#D4D2D6", "#000000", f"{_S3}/%23004AAD/black.png"),
    ("#E8AAAC", "#E1DEDB", "#000000", f"{_S3}/%238994B2/black.png"),
    ("#B8C2DD", "#E1DEDB", "#000000", f"{_S3}/%23004AAD/black.png"),
    ("#626686", "#E1DEDB", "#FFFFFF", f"{_S3}/%23FDEDD4/black.png"),
    ("#E2A9F1", "#E1DEDB", "#000000", f"{_S3}/%23004AAD/black.png"),
    ("#569677", "#FFF6EE", "#FFFFFF", f"{_S3}/%23FDEDD4/black.png"),
    ("#FDEDD4", "#FFF6EE", "#000000", f"{_S3}/%23691A1E/white.png"),
]


HALF_HALF_CONFIG = CreativeTypeConfig(
    name="half_half",
    display_name="Half Half",
    variants={"default": "iiuu1uj0yzwbk"},
    variant_sequence=["default"] * 12,
    style_pool=[
        {"bg_left": bl, "bg_right": br, "text_color": tc}
        for bl, br, tc, _ in _VARIANTS
    ],
    cta_pool=[
        {"button_image": cta} for _, _, _, cta in _VARIANTS
    ],
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
        # Product image(s) - cycles round-robin across creatives
        Slot(name="image.image", source="image.product", batch_creatives=True, generator_config={"aspect_ratio": "9:16"}),
    ],
)

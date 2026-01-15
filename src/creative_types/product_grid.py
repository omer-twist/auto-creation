"""Product grid creative type configuration."""

from ..models.config import CreativeTypeConfig
from ..models.slot import Slot


def _make_style(bg_left, bg_right_1, bg_right_2, bg_right_3, bg_right_4):
    """Helper to create style dict with symmetric bg colors (1&5, 2&6, 3&7, 4&8)."""
    return {
        "bg_left": bg_left,
        "bg_right_1": bg_right_1,
        "bg_right_2": bg_right_2,
        "bg_right_3": bg_right_3,
        "bg_right_4": bg_right_4,
        "bg_right_5": bg_right_1,  # Same as 1
        "bg_right_6": bg_right_2,  # Same as 2
        "bg_right_7": bg_right_3,  # Same as 3
        "bg_right_8": bg_right_4,  # Same as 4
    }


# Color variants (each repeated 3 times = 12 total)
PINK = _make_style("#DA8C90", "#E8AAAC", "#DA8C90", "#827171", "#D4D2D6")
PURPLE = _make_style("#855E89", "#DBD4FD", "#855E89", "#827171", "#D4D2D6")
BLUE = _make_style("#597A9A", "#B5D7E6", "#597A9A", "#827171", "#D4D2D6")
BROWN = _make_style("#362626", "#FDEDD4", "#A69A87", "#827171", "#D4D2D6")


PRODUCT_GRID_CONFIG = CreativeTypeConfig(
    name="product_grid",
    display_name="Product Grid",
    variants={"default": "rmmpciphegoyo"},
    variant_sequence=["default"] * 12,
    style_pool=[
        # Pink (x3)
        PINK, PINK, PINK,
        # Purple (x3)
        PURPLE, PURPLE, PURPLE,
        # Blue (x3)
        BLUE, BLUE, BLUE,
        # Brown (x3)
        BROWN, BROWN, BROWN,
    ],
    cta_pool=[
        # Pink (x3) - bg_right_1 = #E8AAAC
        {"button_image": "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23E8AAAC/black.png"},
        {"button_image": "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23E8AAAC/black.png"},
        {"button_image": "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23E8AAAC/black.png"},
        # Purple (x3) - bg_right_1 = #DBD4FD
        {"button_image": "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23DBD4FD/black.png"},
        {"button_image": "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23DBD4FD/black.png"},
        {"button_image": "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23DBD4FD/black.png"},
        # Blue (x3) - bg_right_1 = #B5D7E6
        {"button_image": "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23B5D7E6/black.png"},
        {"button_image": "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23B5D7E6/black.png"},
        {"button_image": "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23B5D7E6/black.png"},
        # Brown (x3) - bg_right_1 = #FDEDD4
        {"button_image": "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23FDEDD4/black.png"},
        {"button_image": "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23FDEDD4/black.png"},
        {"button_image": "https://creatives-dealogic-assets.s3.amazonaws.com/cta/%23FDEDD4/black.png"},
    ],
    slots=[
        # Main text - varies per creative
        Slot(name="main_text.text", source="text.main_text", batch_creatives=True),
        # 8 product image slots - explicit input_index for each
        # aspect_ratio 1:1 for 270x270 grid cells
        Slot(name="img-right-1.image", source="image.product", generator_config={"input_index": 0, "aspect_ratio": "1:1"}),
        Slot(name="img-right-2.image", source="image.product", generator_config={"input_index": 1, "aspect_ratio": "1:1"}),
        Slot(name="img-right-3.image", source="image.product", generator_config={"input_index": 2, "aspect_ratio": "1:1"}),
        Slot(name="img-right-4.image", source="image.product", generator_config={"input_index": 3, "aspect_ratio": "1:1"}),
        Slot(name="img-right-5.image", source="image.product", generator_config={"input_index": 4, "aspect_ratio": "1:1"}),
        Slot(name="img-right-6.image", source="image.product", generator_config={"input_index": 5, "aspect_ratio": "1:1"}),
        Slot(name="img-right-7.image", source="image.product", generator_config={"input_index": 6, "aspect_ratio": "1:1"}),
        Slot(name="img-right-8.image", source="image.product", generator_config={"input_index": 7, "aspect_ratio": "1:1"}),
        # 9 background color slots - style.* sources vary per creative automatically
        Slot(name="bg-left.background_color", source="style.bg_left"),
        Slot(name="bg-right-1.background_color", source="style.bg_right_1"),
        Slot(name="bg-right-2.background_color", source="style.bg_right_2"),
        Slot(name="bg-right-3.background_color", source="style.bg_right_3"),
        Slot(name="bg-right-4.background_color", source="style.bg_right_4"),
        Slot(name="bg-right-5.background_color", source="style.bg_right_5"),
        Slot(name="bg-right-6.background_color", source="style.bg_right_6"),
        Slot(name="bg-right-7.background_color", source="style.bg_right_7"),
        Slot(name="bg-right-8.background_color", source="style.bg_right_8"),
        # CTA button
        Slot(name="cta.image", source="cta.button_image"),
    ],
)

"""Product cluster creative type configuration."""

import os

from ...models.config import CreativeTypeConfig
from ...models.slot import Slot


PRODUCT_CLUSTER_CONFIG = CreativeTypeConfig(
    name="product_cluster",
    display_name="Product Cluster",
    variants={
        "dark": os.getenv("PLACID_PRODUCT_CLUSTER_TEMPLATE_UUID", ""),
        "light": os.getenv("PLACID_PRODUCT_CLUSTER_TEMPLATE_UUID_WHITE", ""),
    },
    variant_sequence=["dark"] * 6 + ["light"] * 6,  # 6+6 pattern (matching v1)
    style_pool=[
        # Light backgrounds (for dark text template) - first 6
        {"background_color": "#FDEDD4"},
        {"background_color": "#D4D2D6"},
        {"background_color": "#E8AAAC"},
        {"background_color": "#B5D7E6"},
        {"background_color": "#DBD4FD"},
        {"background_color": "#FDD4D4"},
        # Dark backgrounds (for white text template) - last 6
        {"background_color": "#855E89"},
        {"background_color": "#559B82"},
        {"background_color": "#A69A87"},
        {"background_color": "#597A9A"},
        {"background_color": "#827171"},
        {"background_color": "#5B6E82"},
    ],
    # Note: inputs come from generators (INPUTS), collected by serializer
    slots=[
        Slot(
            name="header.text",
            source="text.header",
            optional=True,
            label="Header",
        ),
        Slot(name="main_text.text", source="text.main_text"),
        Slot(
            name="image.image",
            source="image.cluster",
            generator_config={"aspect_ratio": "16:9"},
        ),
        Slot(name="bg.background_color", source="style.background_color"),
    ],
)

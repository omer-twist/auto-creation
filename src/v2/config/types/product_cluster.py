"""Product cluster creative type configuration."""

import os

from ...models.config import CreativeTypeConfig, InputField
from ...models.slot import Slot, SlotUI


PRODUCT_CLUSTER_CONFIG = CreativeTypeConfig(
    name="product_cluster",
    display_name="Product Cluster",
    variants={
        "dark": os.getenv("PLACID_PRODUCT_CLUSTER_TEMPLATE_UUID", ""),
        "light": os.getenv("PLACID_PRODUCT_CLUSTER_TEMPLATE_UUID_WHITE", ""),
    },
    variant_sequence=["dark", "light"] * 6,  # 12 alternating
    inputs=[
        InputField(
            name="product_image_urls",
            type="url_list",
            label="Product Image URLs (1-8)",
            required=True,
        ),
        InputField(
            name="main_lines",
            type="text_list",
            label="Main Text Lines (optional override)",
            required=False,
        ),
    ],
    slots=[
        Slot(
            name="header.text",
            source="text.header",
            ui=SlotUI(
                toggleable=True,
                toggle_label="Include Header",
                toggle_default=True,
                option_name="include_header",
            ),
        ),
        Slot(name="main_text.text", source="text.main_text"),
        Slot(
            name="image.image",
            source="image.cluster",
            generator_config={"aspect_ratio": "16:9"},
        ),
    ],
)

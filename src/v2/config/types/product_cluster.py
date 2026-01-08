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
    variant_sequence=["dark", "light"] * 6,  # 12 alternating
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
    ],
)

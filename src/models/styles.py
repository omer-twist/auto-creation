"""Style configuration for creatives."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Style:
    """Visual style for a standard creative."""

    background_color: str
    text_color: str
    font: str


@dataclass(frozen=True)
class ProductClusterStyle:
    """Visual style for a product cluster creative."""

    background_color: str
    header_color: str
    main_color: str


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


def get_style(index: int) -> Style:
    """Get style by index (cycles if index >= len(STYLES))."""
    return STYLES[index % len(STYLES)]


def get_styles_for_count(count: int) -> list[Style]:
    """Get N styles, cycling through pool if needed."""
    return [get_style(i) for i in range(count)]


# Product Cluster styles (12 total)
# Black text = header #362626, main #523F3F
# White text = header #FFFFFF, main #FFFFFF
PRODUCT_CLUSTER_STYLES: list[ProductClusterStyle] = [
    # Black text styles (6)
    ProductClusterStyle("#FDEDD4", "#362626", "#523F3F"),
    ProductClusterStyle("#D4D2D6", "#362626", "#523F3F"),
    ProductClusterStyle("#E8AAAC", "#362626", "#523F3F"),
    ProductClusterStyle("#B5D7E6", "#362626", "#523F3F"),
    ProductClusterStyle("#DBD4FD", "#362626", "#523F3F"),
    ProductClusterStyle("#FDD4D4", "#362626", "#523F3F"),
    # White text styles (6)
    ProductClusterStyle("#855E89", "#FFFFFF", "#FFFFFF"),
    ProductClusterStyle("#559B82", "#FFFFFF", "#FFFFFF"),
    ProductClusterStyle("#A69A87", "#FFFFFF", "#FFFFFF"),
    ProductClusterStyle("#597A9A", "#FFFFFF", "#FFFFFF"),
    ProductClusterStyle("#827171", "#FFFFFF", "#FFFFFF"),
    ProductClusterStyle("#5B6E82", "#FFFFFF", "#FFFFFF"),
]


def get_product_cluster_styles() -> list[ProductClusterStyle]:
    """Get all 12 product cluster style combinations."""
    return PRODUCT_CLUSTER_STYLES


def get_product_cluster_style(index: int) -> ProductClusterStyle:
    """Get product cluster style by index (cycles if index >= len)."""
    return PRODUCT_CLUSTER_STYLES[index % len(PRODUCT_CLUSTER_STYLES)]


def get_product_cluster_styles_for_count(count: int) -> list[ProductClusterStyle]:
    """Get N product cluster styles, cycling through pool if needed."""
    return [get_product_cluster_style(i) for i in range(count)]

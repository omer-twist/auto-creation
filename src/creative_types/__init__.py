"""Creative types registry."""

from ..models.config import CreativeTypeConfig
from .product_cluster import PRODUCT_CLUSTER_CONFIG
from .product_grid import PRODUCT_GRID_CONFIG

CREATIVE_TYPES: dict[str, CreativeTypeConfig] = {
    "product_cluster": PRODUCT_CLUSTER_CONFIG,
    "product_grid": PRODUCT_GRID_CONFIG,
}


def get_creative_type(name: str) -> CreativeTypeConfig:
    """Get creative type config by name."""
    if name not in CREATIVE_TYPES:
        raise ValueError(f"Unknown creative type: {name}")
    return CREATIVE_TYPES[name]


def list_creative_types() -> list[str]:
    """List all registered creative types."""
    return list(CREATIVE_TYPES.keys())


__all__ = [
    "CREATIVE_TYPES",
    "get_creative_type",
    "list_creative_types",
]

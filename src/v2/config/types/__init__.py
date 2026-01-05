"""Creative types registry."""

from ...models.config import CreativeTypeConfig

CREATIVE_TYPES: dict[str, CreativeTypeConfig] = {}


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

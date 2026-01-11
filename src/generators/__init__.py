"""Generator registry."""

from typing import Type
from .base import Generator

_GENERATORS: dict[str, Type[Generator]] = {}


def _ensure_generators_loaded():
    """Import all generator modules to trigger registration."""
    from . import text  # noqa: F401
    from . import image  # noqa: F401


def register(path: str):
    """Decorator to register a generator."""
    def decorator(cls):
        _GENERATORS[path] = cls
        return cls
    return decorator


def get_generator_class(path: str) -> Type[Generator]:
    """Get generator class by path."""
    _ensure_generators_loaded()
    if path not in _GENERATORS:
        raise ValueError(f"Unknown generator: {path}")
    return _GENERATORS[path]


def list_generators() -> list[str]:
    """List all registered generators."""
    _ensure_generators_loaded()
    return list(_GENERATORS.keys())


__all__ = [
    "Generator",
    "register",
    "get_generator_class",
    "list_generators",
]

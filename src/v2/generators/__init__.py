"""Generator registry."""

from typing import Type
from .base import Generator, GeneratorOption

_GENERATORS: dict[str, Type[Generator]] = {}


def register(path: str):
    """Decorator to register a generator."""
    def decorator(cls):
        _GENERATORS[path] = cls
        return cls
    return decorator


def get_generator_class(path: str) -> Type[Generator]:
    """Get generator class by path."""
    if path not in _GENERATORS:
        raise ValueError(f"Unknown generator: {path}")
    return _GENERATORS[path]


def list_generators() -> list[str]:
    """List all registered generators."""
    return list(_GENERATORS.keys())


__all__ = [
    "Generator",
    "GeneratorOption",
    "register",
    "get_generator_class",
    "list_generators",
]

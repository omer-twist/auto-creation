"""Generator base class and option definition."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..models.context import GenerationContext


@dataclass
class GeneratorOption:
    """Simplified - just toggles for now (is_people_mode, include_header)."""
    name: str
    type: str       # "toggle" for now
    label: str      # UI display text
    default: Any


class Generator(ABC):
    """Base class for generators."""

    OPTIONS: list[GeneratorOption] = []

    @abstractmethod
    def generate(self, context: GenerationContext) -> list[Any]:
        """Generate values for all creatives."""
        pass

    @classmethod
    def get_options(cls) -> list[GeneratorOption]:
        """Get options this generator accepts."""
        return cls.OPTIONS

"""Generator base class."""

from abc import ABC, abstractmethod
from typing import Any

from ..models.context import GenerationContext
from ..models.config import Field


class Generator(ABC):
    """Base class for generators."""

    # Generators declare what inputs they need
    INPUTS: list[Field] = []

    @abstractmethod
    def generate(self, context: GenerationContext) -> list[Any]:
        """Generate values for all creatives."""
        pass

    @classmethod
    def get_inputs(cls) -> list[Field]:
        """Get input fields this generator needs."""
        return cls.INPUTS

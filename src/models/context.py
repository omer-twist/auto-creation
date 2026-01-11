"""Generation context passed to generators."""

from dataclasses import dataclass
from typing import Any

from .topic import Topic


@dataclass
class GenerationContext:
    """Context passed to generators."""
    topic: Topic
    inputs: dict[str, Any]       # Type-specific inputs (e.g., product_image_urls)
    options: dict[str, Any]      # Runtime options (e.g., is_people_mode)
    count: int                   # How many creatives (flexible, not hardcoded)

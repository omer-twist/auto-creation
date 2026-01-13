"""Slot definitions for Placid templates."""

from dataclasses import dataclass
from typing import Any


@dataclass
class Slot:
    """A slot in a Placid template that needs to be filled."""
    name: str                    # Placid layer name (e.g., "header.text", "image.image")
    source: str                  # "text.header", "image.cluster" (dot notation)
    generator_config: dict[str, Any] | None = None  # Generator-specific settings
    # UI options (flattened from SlotUI)
    optional: bool = False       # User can exclude this slot
    label: str | None = None     # Display name for UI toggle
    batch_creatives: bool = False  # If True, generator returns N values (one per creative)

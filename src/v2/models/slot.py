"""Slot definitions for Placid templates."""

from dataclasses import dataclass
from typing import Any


@dataclass
class SlotUI:
    """UI behavior for a slot."""
    toggleable: bool = False
    toggle_label: str | None = None   # UI display text
    toggle_default: bool = True
    option_name: str | None = None    # Key in options dict (e.g., "include_header")


@dataclass
class Slot:
    """A slot in a Placid template that needs to be filled."""
    name: str                    # Placid layer name (e.g., "header.text", "image.image")
    source: str                  # "text.header", "image.cluster" (dot notation)
    ui: SlotUI | None = None
    generator_config: dict[str, Any] | None = None  # Generator-specific settings

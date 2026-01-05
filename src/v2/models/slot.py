"""Slot definitions for Placid templates."""

from dataclasses import dataclass
from typing import Any


@dataclass
class SlotUI:
    """UI behavior for a slot."""
    toggleable: bool = False
    toggle_label: str | None = None
    toggle_default: bool = True


@dataclass
class Slot:
    """A slot in a Placid template that needs to be filled."""
    name: str                    # Placid layer name
    source: str                  # "text/product_cluster", "image/cluster", "style", "topic", "static"
    field: str | None = None     # For multi-output generators or style/topic field
    value: Any = None            # For static source
    ui: SlotUI | None = None
    # Note: Removed transform - uppercase for headers is internal engine logic

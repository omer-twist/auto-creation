"""Creative type configuration."""

from dataclasses import dataclass, field
from typing import Any

from .slot import Slot


@dataclass
class InputField:
    """User-provided input - validation handled by frontend/internal code."""
    name: str
    type: str                    # "text" | "url_list" | "number" | "select"
    label: str                   # UI display text
    required: bool = True


@dataclass
class CreativeTypeConfig:
    """Configuration for a creative type. CreativeType IS the template."""
    name: str                            # Template identifier
    display_name: str
    variants: dict[str, str]             # {"dark": UUID, "light": UUID} - physical Placid files
    variant_sequence: list[str] | None   # ["dark", "light"] * 6, or None for single variant
    slots: list[Slot]
    inputs: list[InputField] = field(default_factory=list)

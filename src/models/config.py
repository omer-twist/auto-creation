"""Creative type configuration."""

from dataclasses import dataclass, field
from typing import Any

from .slot import Slot


@dataclass
class Condition:
    """UI-only gate that controls field visibility."""
    type: str                            # "toggle" or "select"
    label: str
    default: Any = None                  # False for toggle, first option for select
    options: list[str] | None = None     # for select
    show_when: list[str] | None = None   # for select: which values show content


@dataclass
class Field:
    """Generic UI field with optional condition."""
    name: str
    type: str                            # "text", "textarea", "list", "toggle", "select"
    label: str
    required: bool = False
    default: Any = None                  # for toggle/select standalone fields
    options: list[str] | None = None     # for select type
    condition: Condition | None = None   # optional visibility gate


@dataclass
class CreativeTypeConfig:
    """Configuration for a creative type. CreativeType IS the template."""
    name: str                            # Template identifier
    display_name: str
    variants: dict[str, str]             # {"dark": UUID, "light": UUID} - physical Placid files
    variant_sequence: list[str] | None   # ["dark", "light"] * 6, or None for single variant
    slots: list[Slot]
    style_pool: list[dict[str, Any]] | None = None  # Static style values per creative
    cta_pool: list[dict[str, Any]] | None = None  # CTA images per creative
    # Note: Fields are now declared by generators (INPUTS) and collected by serializer

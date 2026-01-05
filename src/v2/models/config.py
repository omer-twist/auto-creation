"""Creative type configuration."""

from dataclasses import dataclass, field

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
    """Configuration for a creative type. THIN - just wiring."""
    name: str
    display_name: str
    template_uuid: str
    slots: list[Slot]
    inputs: list[InputField] = field(default_factory=list)
    style_pool: str = "default"

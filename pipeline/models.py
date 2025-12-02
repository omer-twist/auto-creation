"""Data models for the text generation pipeline."""

from dataclasses import dataclass
from enum import Enum


class EventMode(Enum):
    """Event/campaign mode for text generation."""
    BLACK_FRIDAY = "BLACK_FRIDAY"
    PRIME_DAY = "PRIME_DAY"
    REGULAR = "REGULAR"


class DiscountMode(Enum):
    """Discount display mode."""
    UP_TO_PERCENT = "UP_TO_PERCENT"
    NONE = "NONE"


class PageType(Enum):
    """Page type for content targeting."""
    GENERAL = "GENERAL"
    CATEGORY = "CATEGORY"


@dataclass
class GenerationInput:
    """Input for the text generation pipeline."""
    topic: str
    event_mode: EventMode
    discount_mode: DiscountMode
    discount: str | None  # e.g., "up to 50%"
    page_type: PageType

    def to_user_message(self) -> str:
        """Format as user message for OpenAI."""
        lines = [
            f"Topic: {self.topic}",
            f"Event mode: {self.event_mode.value}",
            f"Discount mode: {self.discount_mode.value}",
            f"Discount: {self.discount or 'N/A'}",
            f"Page type: {self.page_type.value}",
        ]
        return "\n".join(lines)


@dataclass
class TextVariation:
    """Single text output with color assignment."""
    index: int          # 1-9
    text: str
    batch_num: int      # 1, 2, or 3 (internal)
    color_index: int    # 0, 1, or 2 within batch

    @staticmethod
    def from_index(index: int, text: str) -> "TextVariation":
        """Create variation with auto-calculated batch/color mapping."""
        batch_num = ((index - 1) // 3) + 1   # 1-3->1, 4-6->2, 7-9->3
        color_index = (index - 1) % 3        # 0, 1, 2 within batch
        return TextVariation(
            index=index,
            text=text,
            batch_num=batch_num,
            color_index=color_index,
        )


@dataclass
class PipelineResult:
    """Complete output from the 3-stage pipeline."""
    variations: list[TextVariation]  # 9 items
    raw_creator_output: str
    raw_editor_output: str
    raw_final_output: str

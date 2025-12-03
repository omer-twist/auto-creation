"""Data models for the text generation pipeline."""

from dataclasses import dataclass


@dataclass
class GenerationInput:
    """Input for the text generation pipeline."""
    topic: str
    event: str  # e.g., "Black Friday", "Prime Day", "none"
    discount: str  # e.g., "up to 50%", "50%", "24h", "none"
    page_type: str  # "general" or "category"

    def to_user_message(self) -> str:
        """Format as user message for OpenAI."""
        lines = [
            f"Topic: {self.topic}",
            f"Event: {self.event}",
            f"Discount: {self.discount}",
            f"Page type: {self.page_type}",
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

"""Campaign model - a batch of 3 creatives that becomes 1 Monday row."""

from dataclasses import dataclass, field

from .creative import Creative


@dataclass
class Campaign:
    """A campaign with 3 creatives, uploaded as one Monday row."""

    creatives: list[Creative] = field(default_factory=list)
    monday_item_id: str | None = None

"""Campaign - optional grouping utility."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .creative import Creative


@dataclass
class Campaign:
    """A group of creatives. Optional - caller decides if/how to group."""
    creatives: list["Creative"] = field(default_factory=list)
    monday_item_id: str | None = None
    # Future: id, topic_id, created_at, metadata


def group_into_campaigns(creatives: list["Creative"], size: int = 3) -> list[Campaign]:
    """
    Utility to group creatives into campaigns.

    Caller decides if/when to use this.
    Engine does NOT call this - it just returns creatives.
    """
    return [
        Campaign(creatives=creatives[i:i + size])
        for i in range(0, len(creatives), size)
    ]

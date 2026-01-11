"""Simplified Topic - universal fields only."""

from dataclasses import dataclass


@dataclass
class Topic:
    """Universal fields for all creative types."""
    name: str
    event: str
    discount: str
    page_type: str
    url: str = ""

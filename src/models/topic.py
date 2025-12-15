"""Topic model - input for creative generation."""

from dataclasses import dataclass, field

from .campaign import Campaign


@dataclass
class Topic:
    """A topic that generates 4 campaigns of 3 creatives each."""

    name: str
    event: str
    discount: str
    page_type: str
    url: str = ""
    product_urls: list[str] = field(default_factory=list)
    campaigns: list[Campaign] = field(default_factory=list)

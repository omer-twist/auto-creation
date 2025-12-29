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
    creative_type: str = "standard"  # "standard" or "product_cluster"
    product_image_urls: list[str] = field(default_factory=list)  # 8 image URLs for product cluster
    main_lines: list[str] = field(default_factory=list)  # 12 main text lines (skips LLM generation)
    campaigns: list[Campaign] = field(default_factory=list)

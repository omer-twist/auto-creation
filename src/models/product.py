"""Product model - extracted from Amazon URLs."""

from dataclasses import dataclass


@dataclass
class Product:
    """A product extracted from an Amazon URL."""

    url: str
    name: str  # Cleaned product name

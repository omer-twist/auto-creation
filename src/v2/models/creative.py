"""Creative output model - generic, DB-friendly, works for any creative type."""

from dataclasses import dataclass
from typing import Any


@dataclass
class Creative:
    """Generic creative - stores layers dict for any creative type."""
    creative_type: str       # "product_cluster", "banner", etc.
    variant: str             # "dark", "light", "default"
    layers: dict[str, Any]   # Inputs sent to Placid (layer_name -> {prop: value})
    creative_url: str        # Final rendered output from Placid

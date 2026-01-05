"""Creative output model - field names match Placid layers for optimization traceability."""

from dataclasses import dataclass


@dataclass
class Creative:
    """Field names match Placid layers for optimization traceability."""
    # Placid layer values (what we sent)
    main_text: str                        # main_text.text
    background_color: str                 # bg.background_color
    main_text_color: str                  # main_text.text_color
    font: str                             # main_text.font
    header_text: str | None = None        # header.text
    header_text_color: str | None = None  # header.text_color
    cluster_image_url: str | None = None  # image.image (input to Placid)

    # Output (what Placid returns)
    image_url: str = ""                   # The generated creative image

    # Future: id, campaign_id, parent_id (for variations), metadata

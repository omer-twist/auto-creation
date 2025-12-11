def to_slug(text: str) -> str:
    """Convert text to slug format: lowercase, no spaces.

    Example: "Gabby Dollhouse" -> "gabbydollhouse"
    """
    return text.lower().replace(" ", "")

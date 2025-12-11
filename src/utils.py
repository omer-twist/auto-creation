from datetime import date


def to_slug(text: str) -> str:
    """Convert text to slug format: lowercase, no spaces.

    Example: "Gabby Dollhouse" -> "gabbydollhouse"
    """
    return text.lower().replace(" ", "")


def today_date() -> str:
    """Return today's date in Monday.com format (YYYY-MM-DD)."""
    return date.today().isoformat()

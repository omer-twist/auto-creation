"""Load prompts from config files."""

from pathlib import Path


PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"


def load_prompt(stage_name: str) -> str:
    """
    Load prompt for a stage.

    Args:
        stage_name: One of 'creator', 'editor', 'final_toucher'

    Returns:
        The prompt text.

    Raises:
        FileNotFoundError: If prompt file doesn't exist.
    """
    path = PROMPTS_DIR / f"{stage_name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()

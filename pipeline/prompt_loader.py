"""Load prompts from config files."""

from functools import lru_cache
from pathlib import Path


# Prompts directory relative to this file
PROMPTS_DIR = Path(__file__).parent.parent / "config" / "prompts"


class PromptLoader:
    """Load and cache prompts from config files."""

    @staticmethod
    @lru_cache(maxsize=3)
    def load(stage_name: str) -> str:
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

    @classmethod
    def creator(cls) -> str:
        """Load CREATOR stage prompt."""
        return cls.load("creator")

    @classmethod
    def editor(cls) -> str:
        """Load EDITOR stage prompt."""
        return cls.load("editor")

    @classmethod
    def final_toucher(cls) -> str:
        """Load FINAL TOUCHER stage prompt."""
        return cls.load("final_toucher")

    @classmethod
    def reload_all(cls) -> None:
        """Clear cache to reload prompts (for development)."""
        cls.load.cache_clear()

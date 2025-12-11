"""Text generation service - 3-stage LLM pipeline."""

import re
from dataclasses import dataclass
from pathlib import Path

from ..clients.llm import LLMClient
from ..models import Topic


PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class TextGenerationError(Exception):
    """Failed to generate texts."""
    pass


class TSVParseError(Exception):
    """Failed to parse TSV output."""
    def __init__(self, message: str, raw_output: str):
        self.raw_output = raw_output
        super().__init__(message)


@dataclass
class TSVRow:
    """Single row from TSV output."""
    index: int
    text: str


class TextService:
    """Generate 12 text variations using 3-stage LLM pipeline."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def generate_for_topic(self, topic: Topic, max_retries: int = 2) -> list[str]:
        """
        Generate 12 text variations for a topic.

        Returns list of 12 strings.
        """
        creator_output = self._run_stage("creator", topic, None, max_retries)
        creator_rows = self._parse_tsv(creator_output)
        creator_tsv = self._format_tsv(topic.name, creator_rows)

        editor_output = self._run_stage("editor", topic, creator_tsv, max_retries)
        editor_rows = self._parse_tsv(editor_output)
        editor_tsv = self._format_tsv(topic.name, editor_rows)

        final_output = self._run_stage("final_toucher", topic, editor_tsv, max_retries)
        final_rows = self._parse_tsv(final_output)

        total_input, total_output = self.llm.get_token_totals()
        print(f"Token totals: input={total_input}, output={total_output}", flush=True)

        return [row.text for row in final_rows]

    def _run_stage(
        self,
        stage_name: str,
        topic: Topic,
        prev_tsv: str | None,
        max_retries: int,
    ) -> str:
        """Run a stage: build message, call LLM, retry on parse failure."""
        print(f"=== STAGE: {stage_name.upper()} ===", flush=True)

        system_prompt = self._load_prompt(stage_name)

        # Build user message
        user_message = self._build_user_message(topic)
        if prev_tsv:
            user_message = f"{user_message}\n\n{prev_tsv}"
        else:
            user_message = f"{user_message}\nPlease generate 12 TSV lines."

        # Call with retry
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                output = self.llm.call(system_prompt, user_message, label=stage_name.upper())
                self._parse_tsv(output)  # validate
                return output
            except TSVParseError as e:
                last_error = e
                if attempt < max_retries:
                    print(f"  {stage_name} attempt {attempt + 1} failed: {e}. Retrying...", flush=True)

        raise TextGenerationError(f"{stage_name} failed after {max_retries + 1} attempts: {last_error}")

    def _build_user_message(self, topic: Topic) -> str:
        """Build user message from topic."""
        lines = [
            f"Topic: {topic.name}",
            f"Event: {topic.event}",
            f"Discount: {topic.discount}",
            f"Page Type: {topic.page_type}",
        ]
        return "\n".join(lines)

    def _load_prompt(self, stage_name: str) -> str:
        """Load prompt for a stage."""
        path = PROMPTS_DIR / f"{stage_name}.txt"
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8").strip()

    def _parse_tsv(self, content: str) -> list[TSVRow]:
        """Parse TSV content from AI output."""
        rows: list[TSVRow] = []
        lines = content.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip markdown headers
            if line.startswith('#'):
                continue

            # Skip TSV header row
            lower = line.lower()
            if 'variation' in lower and ('#' in lower or 'text' in lower):
                continue
            if lower.startswith('index') and 'text' in lower:
                continue

            # Parse "number\ttext" or "number    text"
            match = re.match(r'^(\d+)\s+(.+)$', line)
            if match:
                index = int(match.group(1))
                text = match.group(2).strip()
                if 1 <= index <= 12 and text:
                    rows.append(TSVRow(index=index, text=text))

        if len(rows) != 12:
            raise TSVParseError(f"Expected 12 rows, got {len(rows)}", raw_output=content)

        indices = sorted(row.index for row in rows)
        if indices != list(range(1, 13)):
            raise TSVParseError(f"Expected indices 1-12, got {indices}", raw_output=content)

        return sorted(rows, key=lambda r: r.index)

    def _format_tsv(self, topic: str, rows: list[TSVRow]) -> str:
        """Format rows as TSV for input to next stage."""
        lines = [
            f"### {topic} — TSV",
            "",
            "Variation #\tText",
        ]
        for row in rows:
            lines.append(f"{row.index}\t{row.text}")
        return '\n'.join(lines)

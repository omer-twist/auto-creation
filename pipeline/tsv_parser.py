"""Parse TSV output between pipeline stages."""

import re

from .models import TSVRow


class TSVParseError(Exception):
    """Failed to parse TSV output."""
    def __init__(self, message: str, raw_output: str):
        self.raw_output = raw_output
        super().__init__(message)


class TSVParser:
    """Parse TSV output from pipeline stages."""

    EXPECTED_ROWS = 12

    @staticmethod
    def parse(content: str) -> list[TSVRow]:
        """
        Parse TSV content from AI output.

        Expected format:
        ### <Topic> — TSV

        Variation #    Text
        1    First variation text...
        2    Second variation text...
        ...
        12   Twelfth variation text...

        Returns list of 12 TSVRow objects.
        Raises TSVParseError if parsing fails.
        """
        rows: list[TSVRow] = []

        # Split into lines and process
        lines = content.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip markdown headers (### Topic — TSV)
            if line.startswith('#'):
                continue

            # Skip TSV header row (Variation #, Index, etc.)
            lower = line.lower()
            if 'variation' in lower and ('#' in lower or 'text' in lower):
                continue
            if lower.startswith('index') and 'text' in lower:
                continue

            # Try to parse as "number\ttext" or "number    text"
            # Handle both tab and multiple spaces as delimiter
            match = re.match(r'^(\d+)\s+(.+)$', line)
            if match:
                index = int(match.group(1))
                text = match.group(2).strip()
                if 1 <= index <= 12 and text:
                    rows.append(TSVRow(index=index, text=text))

        # Validate we got exactly 12 rows
        if len(rows) != TSVParser.EXPECTED_ROWS:
            raise TSVParseError(
                f"Expected {TSVParser.EXPECTED_ROWS} rows, got {len(rows)}",
                raw_output=content
            )

        # Validate indices are 1-12
        indices = sorted(row.index for row in rows)
        if indices != list(range(1, 13)):
            raise TSVParseError(
                f"Expected indices 1-12, got {indices}",
                raw_output=content
            )

        # Sort by index and return
        return sorted(rows, key=lambda r: r.index)

    @staticmethod
    def format_for_next_stage(topic: str, rows: list[TSVRow]) -> str:
        """
        Format rows as TSV for input to next stage.

        Output format:
        ### <Topic> — TSV

        Variation #\tText
        1\t...
        ...
        12\t...
        """
        lines = [
            f"### {topic} — TSV",
            "",
            "Variation #\tText",
        ]
        for row in rows:
            lines.append(f"{row.index}\t{row.text}")
        return '\n'.join(lines)

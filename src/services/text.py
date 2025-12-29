"""Text generation service - 3-stage LLM pipeline."""

import re
from dataclasses import dataclass
from pathlib import Path

from ..clients.llm import LLMClient
from ..models import Product, Topic


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


@dataclass
class TSVRowPaired:
    """Single row from paired TSV output (header + main)."""
    index: int
    header: str
    main_text: str


class TextService:
    """Generate 12 text variations using 3-stage LLM pipeline."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def generate_for_topic(
        self,
        topic: Topic,
        products: list[Product] | None = None,
        max_retries: int = 2,
    ) -> list[str]:
        """
        Generate 12 text variations for a topic.

        Args:
            topic: The topic to generate for.
            products: Optional list of products to inform 4 of 12 creatives.
            max_retries: Max retries per stage.

        Returns list of 12 strings.
        """
        # Pass products ONLY to creator stage
        creator_output = self._run_stage("creator", topic, None, max_retries, products)
        creator_rows = self._parse_tsv(creator_output)
        creator_tsv = self._format_tsv(topic.name, creator_rows)

        # Editor and final_toucher preserve what creator made
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
        products: list[Product] | None = None,
    ) -> str:
        """Run a stage: build message, call LLM, retry on parse failure."""
        print(f"=== STAGE: {stage_name.upper()} ===", flush=True)

        system_prompt = self._load_prompt(stage_name)

        # Build user message (products only for creator stage)
        user_message = self._build_user_message(topic, products)
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

    def _build_product_context(self, products: list[Product]) -> list[str]:
        """Build product context lines for the user message."""
        lines = ["", "Product Context (use in exactly 4 of 12 lines):"]
        for p in products:
            lines.append(f"- {p.name}")
        return lines

    def _build_user_message(
        self,
        topic: Topic,
        products: list[Product] | None = None,
    ) -> str:
        """Build user message from topic and optional products."""
        lines = [
            f"Topic: {topic.name}",
            f"Event: {topic.event}",
            f"Discount: {topic.discount}",
            f"Page Type: {topic.page_type}",
        ]
        if products:
            lines.extend(self._build_product_context(products))
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

    # ===== Product Cluster Text Generation =====

    def generate_for_product_cluster(
        self,
        topic: Topic,
        max_retries: int = 2,
    ) -> list[tuple[str, str]]:
        """
        Generate 12 (header, main_text) pairs for Product Cluster creatives.

        Args:
            topic: The topic to generate for.
            max_retries: Max retries per stage.

        Returns:
            List of 12 (header, main_text) tuples.
        """
        # Creator stage
        creator_output = self._run_product_cluster_stage(
            "product_cluster_creator", topic, None, max_retries
        )
        creator_rows = self._parse_paired_tsv(creator_output)
        creator_tsv = self._format_paired_tsv(topic.name, creator_rows)

        # Editor stage
        editor_output = self._run_product_cluster_stage(
            "product_cluster_editor", topic, creator_tsv, max_retries
        )
        editor_rows = self._parse_paired_tsv(editor_output)
        editor_tsv = self._format_paired_tsv(topic.name, editor_rows)

        # Final toucher stage
        final_output = self._run_product_cluster_stage(
            "product_cluster_final", topic, editor_tsv, max_retries
        )
        final_rows = self._parse_paired_tsv(final_output)

        total_input, total_output = self.llm.get_token_totals()
        print(f"Token totals: input={total_input}, output={total_output}", flush=True)

        return [(row.header, row.main_text) for row in final_rows]

    def _run_product_cluster_stage(
        self,
        stage_name: str,
        topic: Topic,
        prev_tsv: str | None,
        max_retries: int,
    ) -> str:
        """Run a product cluster stage: build message, call LLM, retry on parse failure."""
        print(f"=== STAGE: {stage_name.upper()} ===", flush=True)

        system_prompt = self._load_prompt(stage_name)

        # Build user message
        user_message = self._build_user_message(topic)
        if prev_tsv:
            user_message = f"{user_message}\n\n{prev_tsv}"
        else:
            user_message = f"{user_message}\nPlease generate 12 TSV rows with Header and Main Text."

        # Call with retry
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                output = self.llm.call(system_prompt, user_message, label=stage_name.upper())
                self._parse_paired_tsv(output)  # validate
                return output
            except TSVParseError as e:
                last_error = e
                if attempt < max_retries:
                    print(f"  {stage_name} attempt {attempt + 1} failed: {e}. Retrying...", flush=True)

        raise TextGenerationError(f"{stage_name} failed after {max_retries + 1} attempts: {last_error}")

    def _parse_paired_tsv(self, content: str) -> list[TSVRowPaired]:
        """Parse 3-column TSV content (Variation #, Header, Main Text)."""
        rows: list[TSVRowPaired] = []
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
            if 'variation' in lower and 'header' in lower:
                continue

            # Parse "number\theader\tmain_text"
            parts = line.split('\t')
            if len(parts) >= 3:
                try:
                    index = int(parts[0].strip())
                    header = parts[1].strip()
                    main_text = parts[2].strip()
                    if 1 <= index <= 12 and header and main_text:
                        rows.append(TSVRowPaired(index=index, header=header, main_text=main_text))
                except ValueError:
                    continue

        if len(rows) != 12:
            raise TSVParseError(f"Expected 12 rows, got {len(rows)}", raw_output=content)

        indices = sorted(row.index for row in rows)
        if indices != list(range(1, 13)):
            raise TSVParseError(f"Expected indices 1-12, got {indices}", raw_output=content)

        return sorted(rows, key=lambda r: r.index)

    def _format_paired_tsv(self, topic: str, rows: list[TSVRowPaired]) -> str:
        """Format paired rows as TSV for input to next stage."""
        lines = [
            f"### {topic} — TSV",
            "",
            "Variation #\tHeader\tMain Text",
        ]
        for row in rows:
            lines.append(f"{row.index}\t{row.header}\t{row.main_text}")
        return '\n'.join(lines)

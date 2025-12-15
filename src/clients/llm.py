"""Generic LLM client with provider-agnostic interface."""

from openai import OpenAI


class LLMClient:
    """Generic LLM client. Currently uses OpenAI, interface is provider-agnostic."""

    def __init__(self, api_key: str, model: str = "gpt-5.2"):
        self._client = OpenAI(api_key=api_key)
        self.model = model
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def call(self, system_prompt: str, user_message: str, label: str = "") -> str:
        """Make LLM call and return response text.

        Args:
            system_prompt: System/developer prompt.
            user_message: User message.
            label: Optional label for logging token usage.

        Returns:
            Response text content.
        """
        response = self._client.responses.create(
            model=self.model,
            input=[
                {"role": "developer", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            reasoning={"effort": "medium"},
        )

        # Track tokens
        usage = response.usage
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        if label:
            print(f"  {label}: input={input_tokens}, output={output_tokens}", flush=True)

        return response.output_text.strip()

    def get_token_totals(self) -> tuple[int, int]:
        """Return accumulated (input, output) tokens."""
        return self.total_input_tokens, self.total_output_tokens

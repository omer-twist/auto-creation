"""Product service - fetch product information using OpenAI web search."""

import json
import logging

from ..clients.llm import LLMClient
from ..models.product import Product

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You fetch Amazon product information and return clean product names.

Given URLs, visit each and extract the product name. Clean it:
- Remove brand names (e.g., "PREBOX", "LEGO")
- Remove age ranges like "for Girls Ages 6-12"
- Remove gift phrases like "Perfect Gift for..."
- Keep the essence: what the product actually IS

Return ONLY a JSON array, no other text:
[{"url": "...", "name": "clean product name"}, ...]
"""


class ProductService:
    """Fetch and clean product information using OpenAI web search."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def fetch_products(self, urls: list[str]) -> list[Product]:
        """
        Fetch products from URLs using OpenAI web search.

        Returns list of successfully fetched products (may be empty).
        """
        if not urls:
            return []

        try:
            prompt = self._build_prompt(urls)
            response = self.llm.call_with_web_search(SYSTEM_PROMPT, prompt, label="PRODUCTS")
            return self._parse_response(response)
        except Exception as e:
            logger.warning(f"Failed to fetch products: {e}")
            return []

    def _build_prompt(self, urls: list[str]) -> str:
        """Build the user prompt with URLs."""
        url_list = "\n".join(f"- {url}" for url in urls)
        return f"Fetch product names from these Amazon URLs:\n{url_list}"

    def _parse_response(self, response: str) -> list[Product]:
        """Parse JSON response into Product objects."""
        try:
            # Try to extract JSON from response (in case there's extra text)
            start = response.find("[")
            end = response.rfind("]") + 1
            if start == -1 or end == 0:
                logger.warning("No JSON array found in response")
                return []

            json_str = response[start:end]
            data = json.loads(json_str)

            products = []
            seen_names = set()

            for item in data:
                url = item.get("url") or ""
                name = (item.get("name") or "").strip()

                if name and name.lower() not in seen_names:
                    products.append(Product(url=url, name=name))
                    seen_names.add(name.lower())

            return products

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return []

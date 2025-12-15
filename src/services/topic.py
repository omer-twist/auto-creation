"""Topic generation service - orchestrates text and creative generation."""

from ..clients.llm import LLMClient
from ..clients.creative import CreativeClient
from ..models import Campaign, Creative, Topic
from ..models.styles import get_styles_for_count

from .creative import CreativeService
from .product import ProductService
from .text import TextService


class TopicService:
    """Orchestrate full topic generation."""

    CAMPAIGNS_PER_TOPIC = 4
    CREATIVES_PER_CAMPAIGN = 3

    def __init__(self, llm: LLMClient, creative_client: CreativeClient):
        self.text_service = TextService(llm)
        self.creative_service = CreativeService(creative_client)
        self.product_service = ProductService(llm)

    def generate(self, topic: Topic) -> Topic:
        """
        Generate complete topic with all campaigns and creatives.

        Creates 4 campaigns with 3 creatives each (12 total).
        Returns the topic with campaigns populated.
        """
        total = self.CAMPAIGNS_PER_TOPIC * self.CREATIVES_PER_CAMPAIGN

        # 1. Fetch products if URLs provided
        products = None
        if topic.product_urls:
            products = self.product_service.fetch_products(topic.product_urls)
            if products:
                print(f"Fetched {len(products)} products for context", flush=True)
            else:
                print("No products fetched (fetch failed or no valid URLs)", flush=True)

        # 2. Generate all texts (with optional product context)
        texts = self.text_service.generate_for_topic(topic, products)

        # 3. Get styles
        styles = get_styles_for_count(total)

        # 4. Generate all creatives (batched Placid calls)
        creatives = self.creative_service.generate_batch(texts, styles)

        # 5. Group into campaigns
        topic.campaigns = self._group_into_campaigns(creatives)

        return topic

    def _group_into_campaigns(self, creatives: list[Creative]) -> list[Campaign]:
        """Group creatives into campaigns of CREATIVES_PER_CAMPAIGN each."""
        return [
            Campaign(creatives=creatives[i : i + self.CREATIVES_PER_CAMPAIGN])
            for i in range(0, len(creatives), self.CREATIVES_PER_CAMPAIGN)
        ]

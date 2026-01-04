"""Topic generation service - orchestrates text and creative generation."""

from ..clients.llm import LLMClient
from ..clients.creative import CreativeClient
from ..models import Campaign, Creative, Topic
from ..models.styles import get_styles_for_count, get_product_cluster_styles_for_count
from .. import config

from .creative import CreativeService
from .product import ProductService
from .product_image import ProductImageService
from .text import TextService


class TopicService:
    """Orchestrate full topic generation."""

    CAMPAIGNS_PER_TOPIC = 4
    CREATIVES_PER_CAMPAIGN = 3

    def __init__(
        self,
        llm: LLMClient,
        creative_client: CreativeClient,
        product_image_service: ProductImageService | None = None,
    ):
        self.text_service = TextService(llm)
        self.creative_service = CreativeService(creative_client)
        self.product_service = ProductService(llm)
        self.product_image_service = product_image_service

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

    # ===== Product Cluster Generation =====

    def generate_product_cluster(self, topic: Topic) -> Topic:
        """
        Generate product cluster topic with all campaigns and creatives.

        Creates a single cluster image from 1-8 product URLs, then:
        - Generates 12 text pairs (header + main)
        - Creates 12 creatives using the shared cluster image
        - Groups into 4 campaigns of 3 creatives each

        Returns the topic with campaigns populated.
        """
        if not self.product_image_service:
            raise RuntimeError("ProductImageService required for product cluster generation")

        if not topic.product_image_urls or not 1 <= len(topic.product_image_urls) <= 8:
            raise ValueError(f"Expected 1-8 product image URLs, got {len(topic.product_image_urls or [])}")

        total = self.CAMPAIGNS_PER_TOPIC * self.CREATIVES_PER_CAMPAIGN

        # 1. Generate product cluster image (shared across all creatives)
        print("=== GENERATING PRODUCT CLUSTER IMAGE ===", flush=True)
        cluster_url = self.product_image_service.generate_cluster(
            topic.product_image_urls,
            is_people_mode=topic.is_people_mode,
        )

        # 2. Generate text pairs (header + main_text)
        if topic.main_lines and len(topic.main_lines) == 12:
            # Use user-provided main lines (header = topic name in caps)
            print("=== USING PROVIDED MAIN LINES ===", flush=True)
            text_pairs = [(topic.name.upper(), line) for line in topic.main_lines]
        else:
            # Generate via LLM
            print("=== GENERATING TEXT PAIRS ===", flush=True)
            text_pairs = self.text_service.generate_for_product_cluster(topic)

        # 3. Get product cluster styles
        styles = get_product_cluster_styles_for_count(total)

        # 4. Generate all creatives (batched Placid calls)
        print("=== GENERATING CREATIVES ===", flush=True)
        template_uuid = config.PLACID_PRODUCT_CLUSTER_TEMPLATE_UUID
        template_uuid_white = config.PLACID_PRODUCT_CLUSTER_TEMPLATE_UUID_WHITE
        if not template_uuid:
            raise RuntimeError("PLACID_PRODUCT_CLUSTER_TEMPLATE_UUID not configured")
        if not template_uuid_white:
            raise RuntimeError("PLACID_PRODUCT_CLUSTER_TEMPLATE_UUID_WHITE not configured")

        creatives = self.creative_service.generate_product_cluster_batch(
            text_pairs=text_pairs,
            styles=styles,
            product_image_url=cluster_url,
            template_uuid=template_uuid,
            template_uuid_white=template_uuid_white,
            include_header=topic.include_header,
        )

        # 5. Group into campaigns
        topic.campaigns = self._group_into_campaigns(creatives)

        return topic

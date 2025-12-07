"""Creative generation service - orchestrates text and image generation."""

from clients.llm import LLMClient
from clients.placid import PlacidClient
from models import Campaign, Creative, Topic

from .images import ImageService
from .styles import get_styles
from .text import TextService


class CreativeService:
    """Generate creatives for a topic."""

    def __init__(self, llm: LLMClient, placid: PlacidClient):
        self.text_service = TextService(llm)
        self.image_service = ImageService(placid)

    def generate(self, topic: Topic) -> Topic:
        """
        Generate all creatives for a topic.

        Creates 4 campaigns with 3 creatives each.
        Returns the topic with campaigns populated.
        """
        styles = get_styles()
        texts = self.text_service.generate(topic)
        urls = self.image_service.generate(texts, styles)

        # Group into 4 campaigns of 3 creatives each
        for i in range(0, 12, 3):
            creatives = [
                Creative(
                    text=texts[j],
                    image_url=urls[j],
                    background_color=styles[j].background_color,
                    text_color=styles[j].text_color,
                    font=styles[j].font,
                )
                for j in range(i, i + 3)
            ]
            topic.campaigns.append(Campaign(creatives=creatives))

        return topic

"""Product cluster image generator."""

import requests

from .. import register
from .base import ImageGenerator
from ...models.context import GenerationContext
from ...clients.gemini import GeminiClient
from ...clients.removebg import RemoveBgClient
from ...clients.creative import CreativeClient


@register("image.cluster")
class ClusterImageGenerator(ImageGenerator):
    """Generates product cluster images from product URLs."""

    # INPUTS defined in src/generators/inputs.py (kept separate to avoid heavy imports in serializers)

    def __init__(
        self,
        gemini: GeminiClient | None = None,
        removebg: RemoveBgClient | None = None,
        creative: CreativeClient | None = None,
    ):
        super().__init__(removebg=removebg, creative=creative)
        self.gemini = gemini

    def _generate_raw(self, context: GenerationContext) -> list[bytes]:
        """Download products -> Gemini cluster generation."""
        # Get inputs
        image_urls = context.inputs.get("product_image_urls", [])
        aspect_ratio = context.inputs.get("aspect_ratio", "16:9")
        is_people_mode = context.inputs.get("is_people_mode", False)

        # Validate
        if not 1 <= len(image_urls) <= 8:
            raise ValueError(f"Expected 1-8 image URLs, got {len(image_urls)}")
        if not self.gemini:
            raise ValueError("GeminiClient required for cluster generation")

        # Download images
        product_images = self._download_images(image_urls)

        # Generate cluster via Gemini (single combined image)
        image_bytes = self.gemini.generate_product_cluster(
            product_images=product_images,
            aspect_ratio=aspect_ratio,
            is_people_mode=is_people_mode,
        )
        return [image_bytes]  # Return as list (single image)

    def _download_images(self, urls: list[str]) -> list[bytes]:
        """Download images from URLs to bytes."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        images = []
        for i, url in enumerate(urls):
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                images.append(response.content)
            except requests.RequestException as e:
                raise RuntimeError(f"Failed to download image {i + 1} from {url}: {e}")
        return images

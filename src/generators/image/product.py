"""Product image generator - processes individual product images."""

import requests

from .. import register
from .base import ImageGenerator
from ...models.context import GenerationContext
from ...clients.gemini import GeminiClient
from ...clients.removebg import RemoveBgClient
from ...clients.creative import CreativeClient


@register("image.product")
class ProductImageGenerator(ImageGenerator):
    """Generates clean product images from product URLs.

    Unlike ClusterImageGenerator which combines products into one image,
    this generator processes each product individually and returns multiple URLs.
    The engine's smart indexing distributes them across slots.
    """

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
        """Download and process each product image via Gemini."""
        image_urls = context.inputs.get("product_image_urls", [])
        aspect_ratio = context.inputs.get("aspect_ratio", "1:1")

        if not image_urls:
            raise ValueError("No product_image_urls provided")
        if not self.gemini:
            raise ValueError("GeminiClient required for product image generation")

        results = []
        for i, url in enumerate(image_urls):
            print(f"Processing product image {i + 1}/{len(image_urls)}...", flush=True)

            # Download
            image_bytes = self._download_image(url, i)

            # Gemini single product cleanup
            processed_bytes = self.gemini.generate_single_product(
                product_image=image_bytes,
                aspect_ratio=aspect_ratio,
            )
            results.append(processed_bytes)

        return results

    def _download_image(self, url: str, index: int) -> bytes:
        """Download a single image from URL."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to download image {index + 1} from {url}: {e}")

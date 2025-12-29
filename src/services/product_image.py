"""Product image service - generates product cluster images."""

import requests
from io import BytesIO

from ..clients.gemini import GeminiClient
from ..clients.removebg import RemoveBgClient
from ..clients.creative import CreativeClient


class ProductImageService:
    """Generate product cluster images from product image URLs."""

    def __init__(
        self,
        gemini_client: GeminiClient,
        removebg_client: RemoveBgClient,
        creative_client: CreativeClient,
    ):
        self.gemini = gemini_client
        self.removebg = removebg_client
        self.creative = creative_client

    def generate_cluster(self, image_urls: list[str]) -> str:
        """
        Generate a product cluster image from product image URLs.

        1. Download images from URLs (into memory as bytes)
        2. Send bytes to Nano Banana Pro with clustering prompt
        3. Run result bytes through remove.bg
        4. Upload final bytes to Placid media endpoint
        5. Return Placid-hosted URL

        Args:
            image_urls: List of product image URLs (exactly 8)

        Returns:
            Placid-hosted URL for the cluster image
        """
        if len(image_urls) != 8:
            raise ValueError(f"Expected exactly 8 image URLs, got {len(image_urls)}")

        print(f"Downloading {len(image_urls)} product images...", flush=True)

        # 1. Download all images to bytes
        product_images = self._download_images(image_urls)
        print(f"  Downloaded {len(product_images)} images", flush=True)

        # 2. Generate cluster via Nano Banana Pro
        print("Generating product cluster via Nano Banana Pro...", flush=True)
        cluster_bytes = self.gemini.generate_product_cluster(
            product_images=product_images,
            aspect_ratio="16:9",
        )
        print(f"  Generated cluster image ({len(cluster_bytes)} bytes)", flush=True)

        # 3. Remove background via remove.bg
        print("Removing background via remove.bg...", flush=True)
        clean_bytes = self.removebg.remove_background(cluster_bytes)
        print(f"  Cleaned image ({len(clean_bytes)} bytes)", flush=True)

        # 4. Upload to Placid
        print("Uploading to Placid...", flush=True)
        placid_url = self.creative.upload_media(clean_bytes, "product_cluster.png")
        print(f"  Uploaded: {placid_url}", flush=True)

        return placid_url

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

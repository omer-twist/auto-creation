"""Product image service - generates product cluster images."""

import requests
from io import BytesIO

from PIL import Image

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

    def generate_cluster(self, image_urls: list[str], is_people_mode: bool = False) -> str:
        """
        Generate a product cluster image from product image URLs.

        1. Download images from URLs (into memory as bytes)
        2. Send bytes to Nano Banana Pro with clustering prompt
        3. Run result bytes through remove.bg
        4. Upload final bytes to Placid media endpoint
        5. Return Placid-hosted URL

        Args:
            image_urls: List of product image URLs (1-8)
            is_people_mode: If True, preserve original images (don't extract products from people)

        Returns:
            Placid-hosted URL for the cluster image
        """
        if not 1 <= len(image_urls) <= 8:
            raise ValueError(f"Expected 1-8 image URLs, got {len(image_urls)}")

        print(f"Downloading {len(image_urls)} product images...", flush=True)

        # 1. Download all images to bytes
        product_images = self._download_images(image_urls)
        print(f"  Downloaded {len(product_images)} images", flush=True)

        # 2. Generate cluster via Nano Banana Pro
        print("Generating product cluster via Nano Banana Pro...", flush=True)
        cluster_bytes = self.gemini.generate_product_cluster(
            product_images=product_images,
            aspect_ratio="16:9",
            is_people_mode=is_people_mode,
        )
        print(f"  Generated cluster image ({len(cluster_bytes)} bytes)", flush=True)

        # 3. Remove background via remove.bg
        print("Removing background via remove.bg...", flush=True)
        clean_bytes = self.removebg.remove_background(cluster_bytes)
        print(f"  Cleaned image ({len(clean_bytes)} bytes)", flush=True)

        # 4. Crop transparent areas
        print("Cropping transparent areas...", flush=True)
        cropped_bytes = self._crop_transparent(clean_bytes)
        print(f"  Cropped image ({len(cropped_bytes)} bytes)", flush=True)

        # 5. Upload to Placid
        print("Uploading to Placid...", flush=True)
        placid_url = self.creative.upload_media(cropped_bytes, "product_cluster.png")
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

    def _crop_transparent(self, image_data: bytes) -> bytes:
        """Crop transparent areas from image, keeping only the content bounding box."""
        img = Image.open(BytesIO(image_data))

        if img.mode != "RGBA":
            img = img.convert("RGBA")

        bbox = img.getbbox()
        if not bbox:
            return image_data

        img = img.crop(bbox)

        output = BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()

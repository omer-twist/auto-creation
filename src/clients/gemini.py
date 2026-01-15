"""Gemini Image Generation client (Nano Banana Pro / Gemini 3 Pro Image)."""

import time
from io import BytesIO

from google import genai
from google.genai import types
from PIL import Image


class GeminiClient:
    """Client for generating images via Google's Gemini 3 Pro Image (Nano Banana Pro)."""

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        # Use Gemini 3 Pro Image Preview (Nano Banana Pro)
        # Supports up to 14 input images (5 with high fidelity)
        self.model = "gemini-3-pro-image-preview"

    def _call_with_retry(self, func, max_retries=5, retry_codes=(503, 429)):
        """Retry API calls on transient errors with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                error_str = str(e)
                is_retryable = any(str(code) in error_str for code in retry_codes)

                if not is_retryable or attempt == max_retries - 1:
                    raise

                wait_time = 2 ** attempt  # 1s, 2s, 4s
                print(f"Gemini API error (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s: {e}", flush=True)
                time.sleep(wait_time)

    def generate_product_cluster(
        self,
        product_images: list[bytes],
        aspect_ratio: str = "16:9",
        is_people_mode: bool = False,
    ) -> bytes:
        """
        Generate a product cluster image from multiple product images.

        Args:
            product_images: List of product image bytes (max 8)
            aspect_ratio: Output aspect ratio (default 16:9)
            is_people_mode: If True, preserve original images (don't extract products from people)

        Returns:
            Generated image bytes
        """
        if len(product_images) > 8:
            raise ValueError("Max 8 input images supported")

        # Build the prompt based on mode and number of products
        if is_people_mode:
            # People mode: preserve original images, always side-by-side
            prompt = (
                "Create a new image that places these photos side by side in a horizontal row. "
                "IMPORTANT: Preserve each image exactly as provided - do not modify, crop, or extract elements from them. "
                "Keep consistent spacing between images - approximately half an image width gap between each. "
                "Center the arrangement in the frame. "
                "Use a clean white background. "
                "Output a single combined image."
            )
        elif len(product_images) <= 3:
            # Simple side-by-side layout for 1-3 products
            prompt = (
                "Create a new image that places these products side by side in a horizontal row. "
                "Keep consistent spacing between products - approximately half a product width gap between each. "
                "Center the products in the frame. "
                "Make the products stand straight and upright. "
                "Use a clean white background. "
                "Output a single combined image."
            )
        else:
            # Spread out cluster for 4+ products
            prompt = (
                "Create a new image that arranges all these products in a dynamic, spread-out 3D cluster composition. "
                "Products should be spread wider apart while still forming a cohesive group. "
                "Allow natural overlap with taller items in back, smaller items in front, but keep spacing loose. "
                "Make the products stand straight and look natural together. "
                "Do NOT place them in a tight dense cluster - spread them out horizontally. "
                "Use a clean white background. "
                "Output a single combined image."
            )

        # Convert bytes to PIL images
        pil_images = []
        for img_bytes in product_images:
            img = Image.open(BytesIO(img_bytes))
            pil_images.append(img)

        # Build multimodal content: text prompt + all images
        contents = [prompt]
        for img in pil_images:
            contents.append(img)

        # Generate using Gemini 3 Pro Image with image config (with retry)
        response = self._call_with_retry(
            lambda: self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size="4K",
                    ),
                ),
            )
        )

        # Extract generated image from response
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    return part.inline_data.data

        raise RuntimeError("No image generated by Gemini")

    def generate_single_product(
        self,
        product_image: bytes,
        aspect_ratio: str = "1:1",
    ) -> bytes:
        """
        Generate a clean single product image.

        Args:
            product_image: Product image bytes
            aspect_ratio: Output aspect ratio (default 1:1 for square)

        Returns:
            Generated image bytes (clean product on white background)
        """
        prompt = (
            "Extract the product from this image exactly as is and place it on a clean white background. "
            "Keep the product centered and upright. "
            "Maintain the original product appearance - do not modify its colors, shape, or details. "
            "Output a single clean product image."
        )

        # Convert bytes to PIL image
        img = Image.open(BytesIO(product_image))

        # Build multimodal content: text prompt + image
        contents = [prompt, img]

        # Generate using Gemini 3 Pro Image with image config (with retry)
        response = self._call_with_retry(
            lambda: self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size="4K",
                    ),
                ),
            )
        )

        # Extract generated image from response
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    return part.inline_data.data

        raise RuntimeError("No image generated by Gemini")

"""remove.bg API client for background removal."""

import requests


class RemoveBgClient:
    """Client for removing backgrounds from images via remove.bg API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.remove.bg/v1.0/removebg"

    def remove_background(self, image_data: bytes) -> bytes:
        """
        Remove background from an image.

        Args:
            image_data: Input image bytes

        Returns:
            Image bytes with background removed (PNG with transparency)
        """
        response = requests.post(
            self.base_url,
            files={"image_file": ("image.png", image_data, "image/png")},
            data={"size": "auto", "format": "png"},
            headers={"X-Api-Key": self.api_key},
            timeout=60,
        )

        if response.status_code == 200:
            return response.content

        # Handle errors
        error_msg = f"remove.bg API error: {response.status_code}"
        try:
            error_data = response.json()
            if "errors" in error_data:
                error_msg = f"remove.bg: {error_data['errors']}"
        except Exception:
            pass

        raise RuntimeError(error_msg)

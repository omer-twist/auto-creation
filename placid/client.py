import time

import requests

from .config import ImageVariant


class PlacidClient:
    def __init__(self, api_token: str, template_uuid: str):
        self.api_token = api_token
        self.template_uuid = template_uuid
        self.base_url = "https://api.placid.app/api/rest"

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: dict,
        json: dict | None = None,
        max_retries: int = 5,
    ) -> requests.Response:
        """Make request with exponential backoff on 429 errors."""
        response = None
        for attempt in range(max_retries):
            if method == "POST":
                response = requests.post(url, json=json, headers=headers, timeout=30)
            else:
                response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 429:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                continue

            return response

        return response

    def submit_job(self, text: str, variant: ImageVariant) -> int | None:
        """Submit a single image job. Returns image_id or None on error."""
        url = f"{self.base_url}/{self.template_uuid}"
        headers = self._get_headers()

        payload = {
            "create_now": False,
            "layers": {
                "bg": {
                    "background_color": variant.color_scheme.background_color,
                },
                "text": {
                    "text": text,
                    "text_color": variant.color_scheme.text_color,
                    "font": variant.font.name,
                },
            },
        }

        try:
            response = self._request_with_retry("POST", url, headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("id")
        except requests.RequestException:
            return None

    def poll_job(self, image_id: int) -> tuple[str, str | None, str | None]:
        """Poll a single job. Returns (status, image_url, error)."""
        url = f"{self.base_url}/images/{image_id}"
        headers = self._get_headers()

        try:
            response = self._request_with_retry("GET", url, headers)
            response.raise_for_status()
            data = response.json()

            status = data.get("status", "unknown")
            image_url = data.get("image_url")
            errors = data.get("errors")

            error_msg = None
            if errors:
                error_msg = "; ".join(errors) if isinstance(errors, list) else str(errors)

            return status, image_url, error_msg
        except requests.RequestException as e:
            return "error", None, str(e)

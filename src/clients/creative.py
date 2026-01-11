"""Creative generation client (Placid API)."""

import time

import requests


class CreativeClient:
    """Client for generating creative images (via Placid API)."""

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

    def upload_media(self, image_data: bytes, filename: str = "image.png") -> str:
        """
        Upload image to Placid media endpoint.

        Args:
            image_data: Image bytes to upload
            filename: Filename for the upload

        Returns:
            Placid-hosted URL for the uploaded image
        """
        url = f"{self.base_url}/media"
        headers = {"Authorization": f"Bearer {self.api_token}"}

        files = {"file": (filename, image_data, "image/png")}

        try:
            response = requests.post(url, files=files, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            # Response format: {"media": [{"file_key": "file", "file_id": "https://..."}]}
            media = data.get("media", [])
            if media and len(media) > 0:
                return media[0].get("file_id")
            raise RuntimeError(f"Unexpected Placid response: {data}")
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to upload media to Placid: {e}")

    def submit_generic_job(
        self, template_uuid: str, layers: dict[str, dict]
    ) -> int | None:
        """
        Submit a generic job with arbitrary layers.

        Args:
            template_uuid: Placid template UUID
            layers: Dict of layer_name -> {property: value}

        Returns:
            Job ID or None on error
        """
        url = f"{self.base_url}/{template_uuid}"
        headers = self._get_headers()

        payload = {
            "create_now": False,
            "layers": layers,
        }

        try:
            response = self._request_with_retry("POST", url, headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("id")
        except requests.RequestException:
            return None

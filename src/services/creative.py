"""Creative generation service - transforms texts + styles into creatives via Placid."""

import time

from ..clients.creative import CreativeClient
from ..models import Creative
from ..models.styles import Style


class ImageGenerationError(Exception):
    """Failed to generate images."""

    pass


class CreativeService:
    """Transform texts + styles into creatives via Placid."""

    def __init__(self, client: CreativeClient, poll_interval: int = 20):
        self.client = client
        self.poll_interval = poll_interval

    def generate_one(self, text: str, style: Style) -> Creative:
        """Generate a single creative."""
        url = self._generate_images([text], [style])[0]
        return self._build_creative(text, style, url)

    def generate_batch(self, texts: list[str], styles: list[Style]) -> list[Creative]:
        """
        Generate multiple creatives efficiently (batched Placid calls).

        Args:
            texts: List of text strings.
            styles: List of Style objects (must match length of texts).

        Returns:
            List of Creative objects.
        """
        if len(texts) != len(styles):
            raise ValueError(f"texts ({len(texts)}) and styles ({len(styles)}) must match")

        urls = self._generate_images(texts, styles)
        return [
            self._build_creative(text, style, url)
            for text, style, url in zip(texts, styles, urls)
        ]

    def _build_creative(self, text: str, style: Style, image_url: str) -> Creative:
        """Build a Creative from components."""
        return Creative(
            text=text,
            image_url=image_url,
            background_color=style.background_color,
            text_color=style.text_color,
            font=style.font,
        )

    def _generate_images(self, texts: list[str], styles: list[Style]) -> list[str]:
        """Submit all jobs, poll until done, return URLs."""
        print("Submitting all images...", flush=True)
        job_ids = self._submit_all(texts, styles)

        print("Polling for completion...", flush=True)
        return self._poll_until_done(job_ids)

    def _submit_all(self, texts: list[str], styles: list[Style]) -> list[int]:
        """Submit all Placid jobs, return job IDs."""
        job_ids = []
        for i, (text, style) in enumerate(zip(texts, styles)):
            image_id = self.client.submit_job(text, style)
            if not image_id:
                raise ImageGenerationError(f"Failed to submit image {i + 1}")
            job_ids.append(image_id)
            print(f"  Submitted image {i + 1}", flush=True)
        return job_ids

    def _poll_until_done(self, job_ids: list[int]) -> list[str]:
        """Poll all jobs until complete, return URLs in order."""
        urls: dict[int, str] = {}
        pending = set(job_ids)

        while pending:
            print(f"  Waiting {self.poll_interval}s before polling {len(pending)} images...", flush=True)
            time.sleep(self.poll_interval)

            for job_id in list(pending):
                status, url, error = self.client.poll_job(job_id)

                if status == "finished":
                    urls[job_id] = url
                    pending.remove(job_id)
                    print(f"  Job {job_id} done", flush=True)
                elif status == "error":
                    raise ImageGenerationError(f"Placid error for job {job_id}: {error}")

        return [urls[job_id] for job_id in job_ids]

"""Image generation service - Placid submit and poll."""

import time

from clients.placid import PlacidClient
from .styles import Style


class ImageGenerationError(Exception):
    """Failed to generate images."""
    pass


class ImageService:
    """Generate images using Placid API."""

    def __init__(self, client: PlacidClient, poll_interval: int = 20):
        self.client = client
        self.poll_interval = poll_interval

    def generate(self, texts: list[str], styles: list[Style]) -> list[str]:
        """
        Generate images for all text/style combinations.

        Args:
            texts: List of 12 text strings.
            styles: List of 12 Style objects.

        Returns:
            List of 12 image URLs.
        """
        if len(texts) != len(styles):
            raise ValueError(f"texts ({len(texts)}) and styles ({len(styles)}) must have same length")

        # Submit all jobs
        print("Submitting all images...", flush=True)
        job_ids = self._submit_all(texts, styles)

        # Poll until done
        print("Polling for completion...", flush=True)
        urls = self._poll_until_done(job_ids)

        return urls

    def _submit_all(self, texts: list[str], styles: list[Style]) -> list[int]:
        """Submit all jobs. Returns list of job IDs."""
        job_ids = []
        for i, (text, style) in enumerate(zip(texts, styles)):
            image_id = self.client.submit_job(text, style)
            if not image_id:
                raise ImageGenerationError(f"Failed to submit image {i + 1}")
            job_ids.append(image_id)
            print(f"  Submitted image {i + 1}", flush=True)
        return job_ids

    def _poll_until_done(self, job_ids: list[int]) -> list[str]:
        """Poll all jobs until complete. Returns list of URLs in same order."""
        urls: dict[int, str] = {}  # job_id -> url
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
                # else still pending

        # Return URLs in original order
        return [urls[job_id] for job_id in job_ids]

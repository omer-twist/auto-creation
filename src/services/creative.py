"""Creative generation service - transforms texts + styles into creatives via Placid."""

import time

from ..clients.creative import CreativeClient
from ..models import Creative
from ..models.styles import Style, ProductClusterStyle


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

    # ===== Product Cluster Methods =====

    def generate_product_cluster_batch(
        self,
        text_pairs: list[tuple[str, str]],
        styles: list[ProductClusterStyle],
        product_image_url: str,
        template_uuid: str,
        template_uuid_white: str,
    ) -> list[Creative]:
        """
        Generate multiple product cluster creatives.

        Args:
            text_pairs: List of (header, main_text) tuples.
            styles: List of ProductClusterStyle objects.
            product_image_url: Shared product cluster image URL.
            template_uuid: Product cluster template UUID (black text).
            template_uuid_white: Product cluster template UUID (white text).

        Returns:
            List of Creative objects.
        """
        if len(text_pairs) != len(styles):
            raise ValueError(f"text_pairs ({len(text_pairs)}) and styles ({len(styles)}) must match")

        urls = self._generate_product_cluster_images(
            text_pairs, styles, product_image_url, template_uuid, template_uuid_white
        )
        return [
            self._build_product_cluster_creative(header, main_text, style, url, product_image_url)
            for (header, main_text), style, url in zip(text_pairs, styles, urls)
        ]

    def _build_product_cluster_creative(
        self,
        header: str,
        main_text: str,
        style: ProductClusterStyle,
        image_url: str,
        product_image_url: str,
    ) -> Creative:
        """Build a Creative from product cluster components."""
        return Creative(
            text=header,
            image_url=image_url,
            background_color=style.background_color,
            text_color=style.header_color,
            font="",  # Font handled by template
            text_secondary=main_text,
            text_color_secondary=style.main_color,
            product_image_url=product_image_url,
        )

    def _generate_product_cluster_images(
        self,
        text_pairs: list[tuple[str, str]],
        styles: list[ProductClusterStyle],
        product_image_url: str,
        template_uuid: str,
        template_uuid_white: str,
    ) -> list[str]:
        """Submit all product cluster jobs, poll until done, return URLs."""
        print("Submitting all product cluster images...", flush=True)
        job_ids = self._submit_all_product_cluster(
            text_pairs, styles, product_image_url, template_uuid, template_uuid_white
        )

        print("Polling for completion...", flush=True)
        return self._poll_until_done(job_ids)

    def _submit_all_product_cluster(
        self,
        text_pairs: list[tuple[str, str]],
        styles: list[ProductClusterStyle],
        product_image_url: str,
        template_uuid: str,
        template_uuid_white: str,
    ) -> list[int]:
        """Submit all product cluster Placid jobs, return job IDs."""
        job_ids = []
        for i, ((header, main_text), style) in enumerate(zip(text_pairs, styles)):
            # Route to white text template if header color is white
            use_template = template_uuid_white if style.header_color == "#FFFFFF" else template_uuid
            image_id = self.client.submit_product_cluster_job(
                header_text=header,
                main_text=main_text,
                style=style,
                product_image_url=product_image_url,
                template_uuid=use_template,
            )
            if not image_id:
                raise ImageGenerationError(f"Failed to submit product cluster image {i + 1}")
            job_ids.append(image_id)
            print(f"  Submitted product cluster image {i + 1}", flush=True)
        return job_ids

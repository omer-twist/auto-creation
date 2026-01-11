"""Base class for image generators with shared post-processing."""

from abc import abstractmethod
from io import BytesIO

from PIL import Image

from ..base import Generator
from ...models.context import GenerationContext
from ...clients.removebg import RemoveBgClient
from ...clients.creative import CreativeClient


class ImageGenerator(Generator):
    """Base class for image generators with shared post-processing."""

    def __init__(
        self,
        removebg: RemoveBgClient | None = None,
        creative: CreativeClient | None = None,
    ):
        self.removebg = removebg
        self.creative = creative

    def generate(self, context: GenerationContext) -> list[str]:
        """Template method: generate raw -> post-process -> upload."""
        # 1. Generate raw image bytes (subclass implements)
        image_bytes = self._generate_raw(context)

        # 2. Post-process (shared)
        remove_bg = context.options.get("remove_bg", True)
        crop = context.options.get("crop", True)
        processed_bytes = self._post_process(image_bytes, remove_bg, crop)

        # 3. Upload to Placid
        url = self._upload(processed_bytes)

        # 4. Return single-element list (engine broadcasts)
        return [url]

    @abstractmethod
    def _generate_raw(self, context: GenerationContext) -> bytes:
        """Generate raw image bytes. Subclasses implement this."""
        pass

    def _post_process(self, image_bytes: bytes, remove_bg: bool, crop: bool) -> bytes:
        """Shared post-processing: remove.bg -> crop."""
        if remove_bg:
            if not self.removebg:
                raise ValueError("RemoveBgClient required for background removal")
            image_bytes = self.removebg.remove_background(image_bytes)

        if crop:
            image_bytes = self._crop_transparent(image_bytes)

        return image_bytes

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

    def _upload(self, image_bytes: bytes, filename: str = "image.png") -> str:
        """Upload to Placid."""
        if not self.creative:
            raise ValueError("CreativeClient required for upload")
        return self.creative.upload_media(image_bytes, filename)

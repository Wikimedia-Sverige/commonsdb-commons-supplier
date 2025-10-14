import base64
import logging
from io import BytesIO

import iscc_sdk
from PIL import Image

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    def __init__(self, image_path: str):
        self._image_path = image_path

    def generate(self) -> str | None:
        logger.info(f"Generating thumbnail from image: '{self._image_path}'.")
        full_image = Image.open(self._image_path)
        if full_image.format is None:
            logger.warning("Format of image unknown. "
                           "Skipping thumbnail generation.")
            return None

        thumb = iscc_sdk.image_thumbnail(self._image_path)
        buffer = BytesIO()
        thumb.save(buffer, full_image.format)
        thumb_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        logger.debug("Thumbnail generation done.")

        return thumb_b64

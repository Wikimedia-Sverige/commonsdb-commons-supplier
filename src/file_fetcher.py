import logging
import os

from PIL import Image
from pywikibot import FilePage

logger = logging.getLogger(__name__)


class FileFetcher:
    def fetch_file(self, directory: str, page: FilePage) -> tuple[str, int, int, int]:
        filename = page.title(with_ns=False)
        path = f"{directory}/{filename}"
        logger.info(f"Downloading file: '{filename}'")
        success = page.download(path, url_width=330)
        if not success:
            raise Exception("Failed to download file.")

        image = Image.open(path)
        return path, os.path.getsize(path), image.width, image.height

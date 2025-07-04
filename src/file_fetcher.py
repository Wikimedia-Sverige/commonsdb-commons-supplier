import logging
import os
from tempfile import TemporaryDirectory

from PIL import Image
from pywikibot import FilePage

logger = logging.getLogger(__name__)


class FileFetcher:
    def __init__(self):
        # Create the temporary directory here to make sure it stays around
        # for as long as it's needed.
        self._storage = TemporaryDirectory()

    def fetch_file(self, page: FilePage) -> tuple[str, int, int, int]:
        filename = page.title(with_ns=False)
        path = f"{self._storage.name}/{filename}"
        logger.info(f"Downloading file: '{filename}'")
        success = page.download(path, url_width=330)
        if not success:
            raise Exception("Failed to download file.")

        image = Image.open(path)
        return path, os.path.getsize(path), image.width, image.height

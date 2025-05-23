import logging
from tempfile import TemporaryDirectory

from pywikibot import FilePage

logger = logging.getLogger(__name__)


class FileFetcher:
    def __init__(self):
        # Create the temporary directory here to make sure it stays around
        # for as long as it's needed.
        self._storage = TemporaryDirectory()

    def fetch_file(self, page: FilePage) -> str:
        filename = page.title(with_ns=False)
        path = f"{self._storage.name}/{filename}"
        logger.info(f"Downloading file: '{filename}'")
        page.download(path)
        return path

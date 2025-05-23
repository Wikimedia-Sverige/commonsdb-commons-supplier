import logging
from tempfile import TemporaryDirectory

from pywikibot import FilePage

logger = logging.getLogger(__name__)


class FileFetcher:
    def fetch_file(self, page: FilePage) -> str:
        filename = page.title(with_ns=False)
        storage = TemporaryDirectory()
        path = f"{storage.name}/{filename}"
        logger.info(f"Downloading file: '{filename}'")
        page.download(path)
        return path

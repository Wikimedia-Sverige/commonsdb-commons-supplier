import logging
from tempfile import TemporaryDirectory
from time import time

from pywikibot import FilePage

from declaration_api_connector import DeclarationApiConnector
from declaration_journal import DeclarationJournal
from file_fetcher import FileFetcher
from iscc_generator import IsccGenerator
from metadata_collector import MetadataCollector
from thumbnail_generator import ThumbnailGenerator

logger = logging.getLogger(__name__)


class File:
    def __init__(
        self,
        journal: DeclarationJournal,
        page: FilePage,
        tags: set[str],
        metadata_collector: MetadataCollector,
        api_connector: DeclarationApiConnector
    ):
        self._journal = journal
        self._page = page
        self._tags = tags
        self._metadata_collector = metadata_collector
        self._api_connector = api_connector

        self._extra_public_metadata = {}
        self._declaration = self._journal.get_page_id_match(self._page.pageid)
        self._iscc: str | None = None
        self._file_size: int | None = None
        self._file_width: int | None = None
        self._file_height: int | None = None
        self._download_time: float | None = None

        self._storage = TemporaryDirectory()
        self._path: str | None = None

    def is_in_journal(self) -> bool:
        return self._declaration is not None

    def is_in_registry(self) -> bool:
        return self._declaration is not None \
            and self._declaration.cid is not None

    def prepare_declaration(self):
        self._declaration = self._journal.add_declaration(
            self._tags,
            page_id=self._page.pageid,
            revision_id=self._page.latest_revision_id
        )

    def create_declaration(self):
        self._download_file()
        iscc_time = self._generate_iscc()
        self._generate_tumbnail()

        self._declaration = self._journal.add_declaration(
            self._tags,
            page_id=self._page.pageid,
            revision_id=self._page.latest_revision_id,
            image_hash=self._page.latest_file_info.sha1,
            file_size=self._file_size,
            width=self._file_width,
            height=self._file_height,
            download_time=self._download_time,
            iscc=self._iscc,
            iscc_time=iscc_time
        )

    def _download_file(self):
        download_start_time = time()
        file_fetcher = FileFetcher()
        (
            self._path,
            self._file_size,
            self._file_width,
            self._file_height
        ) = file_fetcher.fetch_file(self._storage.name, self._page)
        self._download_time = time() - download_start_time

    def _generate_iscc(self) -> float:
        if self._path is None:
            raise Exception("File path required.")

        iscc_start_time = time()
        iscc_generator = IsccGenerator(self._path)
        self._iscc = iscc_generator.generate()
        iscc_time = time() - iscc_start_time

        return iscc_time

    def _generate_tumbnail(self):
        if self._path is None:
            raise Exception("File path required.")

        thumbnail_generator = ThumbnailGenerator(self._path)
        thumbnail = thumbnail_generator.generate()
        if thumbnail is not None:
            self._extra_public_metadata["thumbnail"] = thumbnail

    def update_declaration(self):
        if self._declaration is None:
            raise Exception("Declaration required.")

        args = {
            "page_id": self._page.pageid,
            "revision_id": self._page.latest_revision_id,
            "image_hash": self._page.latest_file_info.sha1
        }

        self._download_file()
        self._generate_tumbnail()
        if self._declaration.iscc is None:
            iscc_time = self._generate_iscc()
            args.update({
                "file_size": self._file_size,
                "width": self._file_width,
                "height": self._file_height,
                "download_time": self._download_time,
                "iscc": self._iscc,
                "iscc_time": iscc_time
            })

        self._journal.update_declaration(self._declaration, **args)

    def make_request(self) -> bool:
        if self._declaration is None:
            raise Exception("Declaration required.")

        if self._declaration.iscc is None:
            raise Exception("ISCC required.")

        logger.info("Getting location.")
        location = self._metadata_collector.get_url()
        logger.info("Getting name.")
        name = self._metadata_collector.get_name()
        logger.info("Getting license.")
        license_url = self._metadata_collector.get_license()
        if self._declaration.cid is not None:
            self._extra_public_metadata["supersedes"] = (
                self._declaration.cid
            )
        cid = self._api_connector.request_declaration(
            name,
            self._declaration.iscc,
            location,
            license_url,
            self._extra_public_metadata
        )
        if cid is None:
            return False

        self._journal.update_declaration(self._declaration, cid=cid)
        return True

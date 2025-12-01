#! /usr/bin/env python

import logging
import os
import random
from argparse import ArgumentParser, Namespace
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import time

from dotenv import load_dotenv
from pywikibot import FilePage, Site
from pywikibot.site._basesite import BaseSite
from sqlalchemy.exc import PendingRollbackError

from declaration_api_connector import DeclarationApiConnector
from declaration_journal import DeclarationJournal, create_journal
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
        metadata_collector: MetadataCollector,
        api_connector: DeclarationApiConnector
    ):
        self._journal = journal
        self._page = page
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
            and self._declaration.ingested_cid is not None

    def create(self, tags: set[str]):
        self._download_file()
        iscc_time = self._generate_iscc()
        self._generate_tumbnail()

        self._declaration = self._journal.add_declaration(
            tags,
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

    def update(self):
        if self._declaration is None:
            raise Exception("Declaration reqiured.")

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
            raise Exception("Declaration reqiured.")

        if self._declaration.iscc is None:
            raise Exception("ISCC reqiured.")

        logger.info("Getting location.")
        location = self._metadata_collector.get_url()
        logger.info("Getting name.")
        name = self._metadata_collector.get_name()
        logger.info("Getting license.")
        license_url = self._metadata_collector.get_license()
        if self._declaration.ingested_cid is not None:
            self._extra_public_metadata["supersedes"] = (
                self._declaration.ingested_cid
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

        self._journal.update_declaration(self._declaration, ingested_cid=cid)
        return True


def process_file(
    page: FilePage,
    args: Namespace,
    journal: DeclarationJournal,
    api_connector: DeclarationApiConnector,
    site: BaseSite,
    batch_name: str
) -> bool:
    logger.info(f"Processing '{page.title()}'.")

    metadata_collector = MetadataCollector(site, page)

    file = File(journal, page, metadata_collector, api_connector)
    tags = set(args.tag)
    tags.add(batch_name)
    if not file.is_in_journal():
        file.create(tags)
    else:
        if file.is_in_registry() and not args.update:
            logger.info("Skiping file already in registry.")
            return False

        file.update()

    if args.iscc:
        return False

    return file.make_request()


def get_os_env(name) -> str:
    value = os.getenv(name)
    if value is None:
        raise Exception(f"Required environment variable {name} not set.")

    return value


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--dry", "-d", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--iscc", "-i", action="store_true")
    parser.add_argument("--quit-on-error", "-q", action="store_true")
    parser.add_argument("--tag", "-t", action="append", default=[])
    parser.add_argument("--rate-limit", "-r", type=float)
    parser.add_argument("--limit", "-l", type=int)
    parser.add_argument("--update", "-u", action="store_true")
    parser.add_argument("--sample", "-s", type=int)
    parser.add_argument("files")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="{asctime};{name};{levelname};{message}",
        style="{"
    )

    load_dotenv()
    api_endpoint = get_os_env("API_ENDPOINT")
    api_key = get_os_env("API_KEY")
    member_credentials_path = get_os_env("MEMBER_CREDENTIALS_FILE")
    private_key_path = get_os_env("PRIVATE_KEY_FILE")
    declaration_journal_url = get_os_env("DECLARATION_JOURNAL_URL")

    declaration_journal = create_journal(declaration_journal_url)
    site = Site("commons")
    if os.path.exists(args.files):
        list_file = args.files
        logger.info(f"Reading file list from file: '{list_file}'.")
        with open(list_file) as page:
            if args.sample:
                page = random.choices(page.readlines(), k=args.sample)
            files = [g.strip() for g in page]
        batch_name = f"batch:{Path(list_file).stem}"
    elif declaration_journal.tag_exists(args.files):
        files_tag = args.files
        logger.info(f"Reading file list from journal tag: '{files_tag}'.")
        declarations = declaration_journal.get_declarations(
            files_tag,
            args.sample
        )
        pages = site.load_pages_from_pageids(
            [d.page_id for d in declarations])
        files = [f.title() for f in site.load_pages_from_pageids(
            [d.page_id for d in declarations])]
        batch_name = args.files
    else:
        raise Exception("No valid list file or tag specified.")

    start_total_time = time()
    error_files = []
    files_added = 0
    timestamp = datetime.now().astimezone().replace(microsecond=0).isoformat()
    print(f"START: {timestamp}")
    api_connector = DeclarationApiConnector(
        args.dry,
        api_endpoint,
        api_key,
        member_credentials_path,
        private_key_path,
        args.rate_limit
    )
    # print(f"Processing {len(files)} files.")
    licenses = defaultdict(int)
    for i, page in enumerate(pages):
        # print("FILE:", i + 1, f)
        # progress = f"{i + 1}/{len(files)}"
        # if args.limit:
        #     progress += f" [{files_added + 1}/{args.limit}]"
        # progress += f": {f}"
        # print(progress)
        if page.isRedirectPage():
            page = page.getRedirectTarget()
        page = FilePage(page)
        start_time = time()
        try:
            added_to_registry = process_file(
                page,
                args,
                declaration_journal,
                api_connector,
                site,
                batch_name
            )
            if added_to_registry:
                files_added += 1
        except Exception as e:
            logger.exception(f"Error while processing file: '{page.title()}'.")
            print("ERROR")
            error_files.append(page.title())

            if type(e) is PendingRollbackError:
                # Once this exception occurs all attempts to read from the
                # database fail.
                # TODO: Figure out how to handle these errors if possible.
                logger.exception(
                    "Don't know how to handle this error. Stopping run.")
                break

            if args.quit_on_error:
                break

        finally:
            process_time = time() - start_time
            print(f"File time: {process_time:.2f}")
            if args.limit and files_added == args.limit:
                print(f"Hit limit for declarations made: {args.limit}.")
                break

    print(f"Total time: {time() - start_total_time:.2f}")
    if error_files:
        print(f"{len(error_files)} requests failed. See log for details:")
        print("\n".join(error_files))
    timestamp = datetime.now().astimezone().replace(microsecond=0).isoformat()
    print(f"DONE: {timestamp}")

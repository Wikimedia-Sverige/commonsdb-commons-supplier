#! /usr/bin/env python

import logging
import os
from argparse import ArgumentParser, Namespace
from datetime import datetime
from time import time

from dotenv import load_dotenv
from pywikibot import FilePage, Site

from declaration_api_connector import DeclarationApiConnector
from declaration_journal import DeclarationJournal, create_journal
from file_fetcher import FileFetcher
from iscc_generator import IsccGenerator
from metadata_collector import MetadataCollector

logger = logging.getLogger(__name__)


def process_file(
    commons_filename: str,
    args: Namespace,
    api_key: str,
    member_credentials_path: str,
    private_key_path: str,
    journal: DeclarationJournal
):
    logger.info(f"Processing '{commons_filename}'.")

    site = Site("commons")
    page = FilePage(site, commons_filename)
    metadata_collector = MetadataCollector(site, page)
    api_connector = DeclarationApiConnector(
        args.dry,
        api_key,
        member_credentials_path,
        private_key_path
    )

    matching_page_id = journal.get_image_hash_match(page.latest_file_info.sha1)
    if matching_page_id is not None:
        logger.info(
            f"Image hash is the same as for page id {matching_page_id}. "
            "Not generating ISCC."
        )
        # TODO: get ISCC from journal.
    else:
        # TODO: Maybe add declaration even when it's a duplicate so it
        # doesn't need to be looked up on Commons?
        declaration_id = journal.add_declaration(
            page_id=page.pageid,
            revision_id=page.latest_revision_id
        )
        file_fetcher = FileFetcher()
        path = file_fetcher.fetch_file(page)
        print(f"File size: {page.latest_file_info.size / 1024 / 1024:.0f} MB")

        iscc_generator = IsccGenerator(path)
        logger.info("Generating ISCC.")
        iscc = iscc_generator.generate()

        journal.update_declaration(
            declaration_id,
            image_hash=page.latest_file_info.sha1,
            iscc=iscc
        )

    if args.iscc:
        return

    logger.info("Getting location.")
    location = metadata_collector.get_url()
    logger.info("Getting name.")
    name = metadata_collector.get_name()
    logger.info("Getting license.")
    license_url = metadata_collector.get_license()
    logger.info("Making declaration.")
    api_connector.request_declaration(name, iscc, location, license_url)
    logger.info(f"Done with '{commons_filename}'.")


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
    parser.add_argument("list_file")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="{asctime};{name};{levelname};{message}",
        style="{"
    )

    load_dotenv()
    api_key = get_os_env("API_KEY")
    member_credentials_file = get_os_env("MEMBER_CREDENTIALS_FILE")
    private_key_file = get_os_env("PRIVATE_KEY_FILE")
    declaration_journal_url = get_os_env("DECLARATION_JOURNAL_URL")

    with open(args.list_file) as f:
        files = [g.strip() for g in f]

    start_total_time = time()
    error_files = []
    timestamp = datetime.now().replace(microsecond=0)
    print(f"START: {timestamp}")
    print(f"Processing {len(files)} files.")
    for i, f in enumerate(files):
        declaration_journal = create_journal(declaration_journal_url)
        print(f"{i + 1}/{len(files)}: {f}")
        start_time = time()
        try:
            process_file(
                f,
                args,
                api_key,
                member_credentials_file,
                private_key_file,
                declaration_journal
            )
        except Exception:
            logger.exception(f"Error while processing file: '{f}'.")
            print("ERROR")
            error_files.append(f)
        finally:
            print(f"File time: {time() - start_time:.0f}")
    print(f"Total time: {time() - start_total_time:.0f}")
    if error_files:
        print("Some requests failed. See log for details:")
        print("\n".join(error_files))
    timestamp = datetime.now().replace(microsecond=0)
    print(f"DONE: {timestamp}")

#! /usr/bin/env python

import logging
import os
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path
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


def process_file(
    commons_filename: str,
    args: Namespace,
    journal: DeclarationJournal,
    api_connector: DeclarationApiConnector,
    site: BaseSite,
    batch_name: str
) -> bool:
    logger.info(f"Processing '{commons_filename}'.")

    page = FilePage(site, commons_filename)
    metadata_collector = MetadataCollector(site, page)

    declaration = journal.get_page_id_match(page.pageid)
    if declaration is not None:
        logger.info(
            f"Page id is the same as for declaration with id {declaration.id}."
        )
        if declaration.ingested_cid is not None:
            logger.info("Skipping declaration with ingested cid: "
                        f"{declaration.ingested_cid}")
            return False
    else:
        tags = set(args.tag)
        tags.add(batch_name)
        declaration = journal.add_declaration(
            tags,
            page_id=page.pageid,
            revision_id=page.latest_revision_id,
            image_hash=page.latest_file_info.sha1
        )

    thumbnail = None
    if declaration.iscc is None:
        # Add ISCC.
        matching_declaration = journal.get_image_hash_match(
            page.latest_file_info.sha1
        )
        if (matching_declaration is not None
                and matching_declaration != declaration
                and matching_declaration.iscc is not None):
            # The same image hash should result in the same ISCC. Just use the
            # one we already have instead of generating it again.
            logger.info(
                f"Image hash is the same as for id {matching_declaration.id}. "
                "Using the same ISCC instead of generating."
            )
            journal.update_declaration(
                declaration,
                iscc=matching_declaration.iscc
            )
            iscc = matching_declaration.iscc
        else:
            # Download file and generate ISCC.
            download_start_time = time()
            file_fetcher = FileFetcher()
            path, file_size, width, height = file_fetcher.fetch_file(page)
            download_time = time() - download_start_time

            iscc_start_time = time()
            iscc_generator = IsccGenerator(path)
            logger.info("Generating ISCC.")
            iscc = iscc_generator.generate()
            iscc_time = time() - iscc_start_time

            thumbnail_generator = ThumbnailGenerator(path)
            thumbnail = thumbnail_generator.generate()

            journal.update_declaration(
                declaration,
                file_size=file_size,
                width=width,
                height=height,
                download_time=download_time,
                iscc=iscc,
                iscc_time=iscc_time
            )
    else:
        iscc = declaration.iscc

    if args.iscc:
        # Only generate ISCC.
        return False

    logger.info("Getting location.")
    location = metadata_collector.get_url()
    logger.info("Getting name.")
    name = metadata_collector.get_name()
    logger.info("Getting license.")
    license_url = metadata_collector.get_license()

    extra_public_metadata = {}
    if thumbnail is not None:
        extra_public_metadata["thumbnail"] = thumbnail

    logger.info("Making declaration.")
    cid = api_connector.request_declaration(
        name,
        iscc,
        location,
        license_url,
        extra_public_metadata
    )
    if cid is not None:
        journal.update_declaration(declaration, ingested_cid=cid)
    logger.info(f"Done with '{commons_filename}'.")
    return True


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
        with open(list_file) as f:
            files = [g.strip() for g in f]
        batch_name = f"batch:{Path(list_file).stem}"
    elif declaration_journal.tag_exists(args.files):
        files_tag = args.files
        logger.info(f"Reading file list from journal tag: '{files_tag}'.")
        declarations = declaration_journal.get_declarations(files_tag)
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
    print(f"Processing {len(files)} files.")
    for i, f in enumerate(files):
        progress = f"{i + 1}/{len(files)}"
        if args.limit:
            progress += f" [{files_added + 1}/{args.limit}]"
        progress += f": {f}"
        print(progress)
        start_time = time()
        try:
            added_to_registry = process_file(
                f,
                args,
                declaration_journal,
                api_connector,
                site,
                batch_name
            )
            if added_to_registry:
                files_added += 1
        except Exception as e:
            logger.exception(f"Error while processing file: '{f}'.")
            print("ERROR")
            error_files.append(f)

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
        print("Some requests failed. See log for details:")
        print("\n".join(error_files))
    timestamp = datetime.now().astimezone().replace(microsecond=0).isoformat()
    print(f"DONE: {timestamp}")

#! /usr/bin/env python

import logging
import os
import random
import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path
from time import time

import urllib3
from dotenv import load_dotenv
from pywikibot import FilePage, Site
from pywikibot.page import Category
from pywikibot.pagegenerators import (
    PagesFromPageidGenerator,
    PagesFromTitlesGenerator,
    PreloadingGenerator
)
from pywikibot.site import BaseSite
from sqlalchemy.exc import PendingRollbackError

from declaration_api_connector import DeclarationApiConnector
from declaration_journal import DeclarationJournal, create_journal
from file import File
from metadata_collector import MetadataCollector

logger = logging.getLogger(__name__)

# Results for processing files.
DECLARED = "DECLARED"
FAILED = "FAILED"
ONLY_ISCC = "ONLY_ISCC"
SKIPPED = "SKIPPED"
PREPARED = "PREPARED"


def process_file(
    page: FilePage,
    args: Namespace,
    journal: DeclarationJournal,
    api_connector: DeclarationApiConnector,
    site: BaseSite,
    batch_name: str,
    prepare: bool = False
) -> str:
    logger.info(f"Processing '{page.title()}'.")

    metadata_collector = MetadataCollector(site, page)

    tags = set(args.tag)
    tags.add(batch_name)
    file = File(journal, page, tags, metadata_collector, api_connector)

    if not file.is_in_journal():
        if prepare:
            file.prepare_declaration()
            return PREPARED

        file.create_declaration()
    else:
        if prepare:
            logger.info("Skipping file already in journal.")
            return SKIPPED

        if file.is_in_registry() and not args.update:
            logger.info("Skipping file already in registry.")
            return SKIPPED

        file.update_declaration()

    if args.iscc:
        return ONLY_ISCC

    if file.make_request():
        return DECLARED
    else:
        return FAILED


def get_os_env(name: str, optional: bool = False) -> str:
    value = os.getenv(name)
    if value is None:
        if optional:
            return ""

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
    parser.add_argument("--prepare", "-p", action="store_true")
    parser.add_argument("--recurse-categories", "-c", action="store_true")
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
    public_key_path = get_os_env("PUBLIC_KEY_FILE")
    declaration_journal_url = get_os_env("DECLARATION_JOURNAL_URL")
    tsa_url = get_os_env("TSA_URL")
    tsa_skip_verify = bool(get_os_env("TSA_SKIP_VERIFY", True))

    if tsa_skip_verify:
        urllib3.disable_warnings()
    declaration_journal = create_journal(declaration_journal_url)
    site = Site("commons")
    number_of_files = None
    if os.path.exists(args.files):
        list_file = args.files
        logger.info(f"Reading file list from file: '{list_file}'.")
        with open(list_file) as f:
            titles = f.readlines()
            if args.sample:
                sample_size = min(args.sample, len(titles))
                titles = random.sample(titles, sample_size)
            number_of_files = len(titles)
            pages = PreloadingGenerator(PagesFromTitlesGenerator(titles, site))
        batch_name = f"batch:{Path(list_file).stem}"
    elif args.files.startswith("Category:"):
        category = Category(site, args.files)
        category_depth = 100 if args.recurse_categories else 0
        pages = category.members(
            recurse=category_depth,  # pyright: ignore[reportArgumentType]
            member_type="file"
        )
        batch_name = f"batch:category-{category.pageid}"
    elif declaration_journal.tag_exists(args.files):
        files_tag = args.files
        logger.info(f"Reading file list from journal tag: '{files_tag}'.")
        only_not_declared = not args.update
        declarations = declaration_journal.get_declarations(
            files_tag,
            args.sample,
            only_not_declared=only_not_declared
        )
        number_of_files = len(declarations)
        pages = PreloadingGenerator(PagesFromPageidGenerator(
            [d.page_id for d in declarations],
            site
        ))
        batch_name = args.files
    else:
        raise Exception("No valid list file, tag or category specified.")

    start_total_time = time()
    error_files = []
    skipped_files = []
    files_declared = 0
    timestamp = datetime.now().astimezone().replace(microsecond=0).isoformat()
    breaking_error = False
    print(f"START: {timestamp}")
    api_connector = DeclarationApiConnector(
        args.dry,
        api_endpoint,
        api_key,
        member_credentials_path,
        private_key_path,
        public_key_path,
        tsa_url,
        tsa_skip_verify,
        args.rate_limit
    )
    if number_of_files:
        print(f"Processing {number_of_files} files.")
    for i, page in enumerate(pages):
        if number_of_files:
            progress = f"{i + 1}/{number_of_files}"
        else:
            progress = f"{i + 1}"
        if args.limit:
            progress += f" [{files_declared + 1}/{args.limit}]"
        progress += f" {page.title()}"
        print(progress)

        start_time = time()
        try:
            page = FilePage(page)
            process_result = process_file(
                page,
                args,
                declaration_journal,
                api_connector,
                site,
                batch_name,
                args.prepare
            )
            if process_result == DECLARED:
                files_declared += 1
            elif process_result == SKIPPED:
                print("SKIP")
                skipped_files.append(page.title())
        except Exception as e:
            logger.exception(f"Error while processing file: '{page.title()}'.")
            print("ERROR")
            error_files.append(page.title())

            if type(e) is PendingRollbackError:
                logger.error("Rolling back session due to error.")
                logger.exception(e)
                declaration_journal.rollback_session()

            if args.quit_on_error:
                break

        finally:
            process_time = time() - start_time
            print(f"File time: {process_time:.2f}")
            if args.limit and files_declared == args.limit:
                print(f"Hit limit for declarations made: {args.limit}.")
                break

    print(f"Total time: {time() - start_total_time:.2f}")
    print(f"{files_declared} files declared.")
    if skipped_files:
        print(f"{len(skipped_files)} files skipped:")
        print("\n".join(skipped_files))
    if error_files:
        print(f"{len(error_files)} requests failed. See log for details:")
        print("\n".join(error_files))
    timestamp = datetime.now().astimezone().replace(microsecond=0).isoformat()
    print(f"DONE: {timestamp}")

    if breaking_error:
        sys.exit(1)

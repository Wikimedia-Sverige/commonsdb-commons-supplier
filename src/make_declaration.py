import logging
from argparse import ArgumentParser
from tempfile import TemporaryDirectory
from time import time

from pywikibot import FilePage, Site

from declaration_api_connector import DeclarationApiConnector
from iscc_generator import IsccGenerator
from metadata_collector import MetadataCollector

logger = logging.getLogger(__name__)


def process_file(commons_filename, args):
    logger.info(f"Processing '{commons_filename}'.")
    site = Site()
    page = FilePage(site, commons_filename)
    filename = page.title(with_ns=False)
    storage = TemporaryDirectory()
    path = f"{storage.name}/{filename}"
    logger.info(f"Downloading file: '{filename}'")
    page.download(path)
    print(f"File size: {page.latest_file_info.size / 1024 / 1024:.0f} MB")

    metadata_collector = MetadataCollector(filename)
    iscc_generator = IsccGenerator(path)
    api_connector = DeclarationApiConnector(args.dry)

    logger.info("Getting name.")
    name = metadata_collector.get_name()
    logger.info("Getting location.")
    location = metadata_collector.get_url()
    logger.info("Getting license.")
    license_url = metadata_collector.get_license()
    logger.info("Generating ISCC.")
    iscc = iscc_generator.generate()
    logger.info("Making declaration.")
    api_connector.request_declaration(name, iscc, location, license_url)
    logger.info(f"Done with '{commons_filename}'.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="{asctime};{name};{levelname};{message}",
        style="{"
    )
    parser = ArgumentParser()
    parser.add_argument("--dry", "-d", action="store_true")
    args = parser.parse_args()

    with open("files.txt") as f:
        files = [g.strip() for g in f]

    start_total_time = time()
    error_files = []
    print(f"Processing {len(files)} files.")
    for i, f in enumerate(files):
        print(f"{i + 1}/{len(files)}: {f}")
        start_time = time()
        try:
            process_file(f, args)
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

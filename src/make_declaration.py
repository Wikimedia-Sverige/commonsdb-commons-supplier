import logging
from pathlib import Path
from pywikibot import Site, FilePage

from declaration_api_connector import DeclarationApiConnector
from iscc_generator import IsccGenerator
from metadata_collector import MetadataCollector

logger = logging.getLogger(__name__)


def process_file(commons_filename):
    site = Site()
    page = FilePage(site, commons_filename)
    filename = page.title(with_ns=False)
    path = f"../files/{filename}"
    if not Path(path).exists():
        logger.info(f"Downloading file: '{filename}'")
        page.download(path)

    metadata_collector = MetadataCollector(filename)
    iscc_generator = IsccGenerator(path)
    api_connector = DeclarationApiConnector()

    name = metadata_collector.get_name()
    location = metadata_collector.get_url()
    license_url = metadata_collector.get_license()
    iscc = iscc_generator.generate()
    api_connector.request_declaration(name, iscc, location, license_url)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="{asctime};{name};{levelname};{message}",
        style="{"
    )
    files = [
        "Stockholm September 2013 - panoramio (11).jpg",
        "File:Stockholm 8887 (9861761014).jpg",
        "File:Johannes Vermeer - Het melkmeisje - Google Art Project.jpg",
        "File:Johannes Vermeer - Het melkmeisje - Google Art Project (fragment).jpg",
        "File:Netherlands-4205 - Milkmaid (11715339273).jpg",
        "File:Johannes Vermeer - Het melkmeisje - Google Art Project.png",
        "File:Domkyrkan Karlstad.JPG",
        "File:Hallsbergs tågstation.JPG",
        "File:Oregrunds kyrka.jpg",
        "File:Litslena kyrka vinter 02.jpg"
    ]
    for f in files:
        print(f)
        try:
            process_file(f)
        except Exception:
            logger.warning(f"Error while processing file: '{f}'.")

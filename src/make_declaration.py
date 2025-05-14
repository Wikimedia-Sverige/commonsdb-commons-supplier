import logging
from pathlib import Path

from declaration_api_connector import DeclarationApiConnector
from iscc_generator import IsccGenerator
from metadata_collector import MetadataCollector


def process_file(path):
    filename = Path(path).name

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
    process_file("...")

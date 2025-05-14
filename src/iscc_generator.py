import logging
import sys

import iscc_sdk

logger = logging.getLogger(__name__)


class IsccGenerator:
    def __init__(self, image_path: str):
        self._image_path = image_path

    def generate(self) -> str:
        logger.info(f"Generating ISCC from image: '{self._image_path}'.")
        iscc_meta = iscc_sdk.code_iscc(self._image_path)
        logger.debug("ISCC generation done.")
        return iscc_meta.iscc


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="{asctime};{name};{levelname};{message}",
        style="{"
    )

    generator = IsccGenerator()
    print(generator.generate(sys.argv[1]))

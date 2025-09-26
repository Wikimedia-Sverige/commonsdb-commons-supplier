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
        if iscc_meta.iscc is None:
            raise Exception("ISCC generation failed.")

        return iscc_meta.iscc


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="{asctime};{name};{levelname};{message}",
        style="{"
    )

    generator = IsccGenerator(sys.argv[1])
    print(generator.generate())

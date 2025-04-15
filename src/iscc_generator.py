import logging
import sys

import iscc_sdk

logger = logging.getLogger(__name__)


class IsccGenerator:
    def generate(self, image_path):
        logger.info(f"Generating ISCC from image: '{image_path}'.")
        iscc_meta = iscc_sdk.code_iscc(image_path)
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

import sys

import iscc_sdk


class IsccGenerator:
    def generate(self, image_path):
        iscc_meta = iscc_sdk.code_iscc(image_path)
        return iscc_meta.iscc


if __name__ == "__main__":
    generator = IsccGenerator()
    print(generator.generate(sys.argv[1]))

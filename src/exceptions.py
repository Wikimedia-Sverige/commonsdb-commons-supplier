class ReadFileError(Exception):
    def __init__(self, path):
        super().__init__(f"Failed reading file: '{path}'")

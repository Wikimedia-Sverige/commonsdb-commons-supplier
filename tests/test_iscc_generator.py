import pytest
from iscc_sdk import IsccMeta

from iscc_generator import IsccGenerator

ISCC = "ISCC:ABCDEFGHIJ"


@pytest.fixture
def iscc_code(monkeypatch):
    iscc_meta = IsccMeta()
    iscc_meta.iscc = ISCC
    monkeypatch.setattr("iscc_sdk.code_iscc", lambda a: iscc_meta)


def test_generate_iscc(iscc_code):
    iscc_generator = IsccGenerator()
    iscc = iscc_generator.generate("/path/file.img")

    assert iscc == ISCC

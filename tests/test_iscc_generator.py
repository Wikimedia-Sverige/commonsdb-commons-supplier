import pytest
from iscc_sdk import IsccMeta

from iscc_generator import IsccGenerator


@pytest.fixture
def iscc_code(monkeypatch):
    iscc_meta = IsccMeta()
    iscc_meta.iscc = "ISCC:ABCDEFGHIJ"
    monkeypatch.setattr("iscc_sdk.code_iscc", lambda a: iscc_meta)


def test_generate_iscc(iscc_code):
    iscc_generator = IsccGenerator("/path/file.img")
    iscc = iscc_generator.generate()

    assert iscc == "ISCC:ABCDEFGHIJ"

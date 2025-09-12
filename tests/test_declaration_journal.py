from datetime import datetime
from unittest import TestCase

from declaration_journal import Declaration, Tag, create_journal


class DeclarationJournalTestCase(TestCase):
    def setUp(self):
        self._declaration_journal = create_journal("sqlite:///:memory:")

    def _add_declaration(self, **kwargs):
        now = datetime.now()
        fields = {
            "page_id": 123,
            "revision_id": 456,
            "created_timestamp": now,
            "updated_timestamp": now
        }
        fields.update(kwargs)
        declaration = Declaration(**fields)
        self._declaration_journal._session.add(declaration)
        return declaration

    def test_add_declaration(self):
        self._declaration_journal.add_declaration(
            {"tag-1", "tag-2"},
            page_id=123,
            revision_id=456,
            image_hash="hash123456789"
        )
        self._declaration_journal.add_declaration(
            {"tag-3"},
            page_id=234,
            revision_id=567,
            image_hash="hash234567890"
        )

        declarations = self._declaration_journal.get_declarations()

        assert declarations[0].tags == {Tag(label="tag-1"), Tag(label="tag-2")}
        assert declarations[0].page_id == 123
        assert declarations[0].revision_id == 456
        assert declarations[0].image_hash == "hash123456789"
        assert declarations[1].tags == {Tag(label="tag-3")}
        assert declarations[1].page_id == 234
        assert declarations[1].revision_id == 567
        assert declarations[1].image_hash == "hash234567890"

    def test_update_declaration(self):
        declaration = self._add_declaration(page_id=123, revision_id=456)
        self._add_declaration(page_id=234, revision_id=567)

        self._declaration_journal.update_declaration(
            declaration,
            revision_id=678
        )
        declarations = self._declaration_journal.get_declarations()

        assert declarations[0].page_id == 123
        assert declarations[0].revision_id == 678
        assert declarations[1].page_id == 234
        assert declarations[1].revision_id == 567

    def test_get_image_hash_match(self):
        declaration = self._add_declaration(image_hash="hash123456789")

        match = self._declaration_journal.get_image_hash_match("hash123456789")

        assert match == declaration

    def test_get_image_hash_match_no_match(self):
        self._add_declaration(image_hash="hash123456789")

        match = self._declaration_journal.get_image_hash_match("hashOTHER")

        assert match is None

    def test_get_page_id_match(self):
        declaration = self._add_declaration(page_id=123)

        match = self._declaration_journal.get_page_id_match(123)

        assert match == declaration

    def test_get_page_id_match_no_match(self):
        self._add_declaration(page_id=123)

        match = self._declaration_journal.get_page_id_match(234)

        assert match is None

    def test_tag_exists(self):
        tag = Tag(label="tag-1")
        self._declaration_journal._session.add(tag)

        assert self._declaration_journal.tag_exists("tag-1") is True
        assert self._declaration_journal.tag_exists("tag-2") is False

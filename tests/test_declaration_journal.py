from unittest import TestCase

from declaration_journal import create_journal


class DeclarationJournalTestCase(TestCase):
    def setUp(self):
        self._declaration_journal = create_journal("sqlite:///:memory:")

    def test_add_declaration(self):
        self._declaration_journal.add_declaration(
            page_id=123,
            revision_id=456,
            image_hash="hash123456789"
        )
        self._declaration_journal.add_declaration(
            page_id=234,
            revision_id=567,
            image_hash="hash234567890"
        )

        declarations = self._declaration_journal.get_declarations()

        assert declarations[0].page_id == 123
        assert declarations[0].revision_id == 456
        assert declarations[0].image_hash == "hash123456789"
        assert declarations[1].page_id == 234
        assert declarations[1].revision_id == 567
        assert declarations[1].image_hash == "hash234567890"

    def test_update_declaration(self):
        declaration = self._declaration_journal.add_declaration(
            page_id=123,
            revision_id=456,
            image_hash="hash123456789"
        )
        self._declaration_journal.add_declaration(
            page_id=234,
            revision_id=567,
            image_hash="hash234567890"
        )

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
        declaration = self._declaration_journal.add_declaration(
            page_id=123,
            revision_id=456,
            image_hash="hash123456789"
        )

        match = self._declaration_journal.get_image_hash_match("hash123456789")

        assert match == declaration

    def test_get_image_hash_match_no_match(self):
        self._declaration_journal.add_declaration(
            page_id=123,
            revision_id=456,
            image_hash="hash123456789"
        )

        match = self._declaration_journal.get_image_hash_match("hashOTHER")

        assert match is None

    def test_get_page_id_match(self):
        declaration = self._declaration_journal.add_declaration(
            page_id=123,
            revision_id=456,
            image_hash="hash123456789"
        )

        match = self._declaration_journal.get_page_id_match(123)

        assert match == declaration

    def test_get_page_id_match_no_match(self):
        self._declaration_journal.add_declaration(
            page_id=123,
            revision_id=456,
            image_hash="hash123456789"
        )

        match = self._declaration_journal.get_page_id_match(234)

        assert match is None

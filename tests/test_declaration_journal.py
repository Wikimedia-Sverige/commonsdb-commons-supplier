from unittest import TestCase

from declaration_journal import create_journal


class DeclarationJournalTestCase(TestCase):
    def setUp(self):
        self._declaration_journal = create_journal("sqlite:///:memory:")

    def test_add_declaration(self):
        self._declaration_journal.add_declaration(
            page_id=123,
            revision_id=456
        )
        self._declaration_journal.add_declaration(
            page_id=234,
            revision_id=567
        )

        declarations = self._declaration_journal.get_declarations()

        assert declarations[0].page_id == 123
        assert declarations[0].revision_id == 456
        assert declarations[1].page_id == 234
        assert declarations[1].revision_id == 567

    def test_update_declaration(self):
        declaration_id = self._declaration_journal.add_declaration(
            page_id=123,
            revision_id=456
        )
        self._declaration_journal.add_declaration(
            page_id=234,
            revision_id=567
        )
        self._declaration_journal.update_declaration(
            declaration_id,
            revision_id=678
        )

        declarations = self._declaration_journal.get_declarations()

        assert declarations[0].page_id == 123
        assert declarations[0].revision_id == 678
        assert declarations[1].page_id == 234
        assert declarations[1].revision_id == 567

    def test_get_image_hash_match(self):
        declaration_id = self._declaration_journal.add_declaration(
            page_id=123,
            revision_id=456
        )
        self._declaration_journal.update_declaration(
            declaration_id,
            image_hash="hash123456789"
        )

        match = self._declaration_journal.get_image_hash_match("hash123456789")

        assert match == 123

    def test_get_image_hash_match_no_match(self):
        self._declaration_journal.add_declaration(
            page_id=123,
            revision_id=456
        )

        match = self._declaration_journal.get_image_hash_match("hashOTHER")

        assert match is None

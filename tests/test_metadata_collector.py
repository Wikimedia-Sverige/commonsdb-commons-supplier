from unittest import TestCase
from unittest.mock import PropertyMock, patch

import pytest
from pywikibot.exceptions import NoPageError

from metadata_collector import MetadataCollector, MissingMetadataError


class MetadataCollectorTestCase(TestCase):
    def setUp(self):
        file_page_patcher = patch("pywikibot.FilePage")
        self.FilePage = file_page_patcher.start()
        site_patcher = patch("pywikibot.Site")
        self.Site = site_patcher.start()
        request_patcher = patch("metadata_collector.Request")
        self.Request = request_patcher.start()
        self._responses = {}
        self.Request.return_value.submit.side_effect = self._response

    def tearDown(self):
        patch.stopall()

    def _response(self, *args, **kwargs):
        parameters = self.Request.call_args.kwargs.get("parameters")
        if parameters.get("action") == "wbgetentities":
            ids = parameters.get("ids", "")
            return self._responses.get(ids)

    def _mock_response(
        self,
        entity_id,
        statements=None,
        claims=None,
        labels=None
    ):
        entity = {}
        if statements:
            response_statements = {}
            for k, v in statements.items():
                if isinstance(v, list):
                    response_statements[k] = [{
                        "mainsnak": {
                            "datavalue": {
                                "value": w
                            }
                        }
                    } for w in v]
                else:
                    response_statements[k] = [{
                        "mainsnak": {
                            "datavalue": {
                                "value": v
                            }
                        }
                    }]
            entity["statements"] = response_statements

        if claims:
            response_claims = {}
            for k, v in claims.items():
                response_claims[k] = [{
                    "mainsnak": {
                        "datavalue": {
                            "value": v
                        }
                    }
                }]
            entity["claims"] = response_claims

        if labels:
            response_labels = {}
            for k, v in labels.items():
                response_labels[k] = {"value": v}
            entity["labels"] = response_labels

        response = {
            "entities": {
                entity_id: entity
            }
        }
        self._responses[entity_id] = response

    def _create_metadata_collector(self, filename):
        site = self.Site()
        page = self.FilePage(site, filename)
        page.title.return_value = filename
        return MetadataCollector(site, page)

    def test_get_url(self):
        self.FilePage.return_value.latest_file_info.descriptionshorturl = "https://commons.wikimedia.org/wiki/Special:Redirect/page/123"  # noqa: E501
        metadata_collector = self._create_metadata_collector(
            "Image on Commons.jpeg"
        )

        url = metadata_collector.get_url()

        assert url == "https://commons.wikimedia.org/wiki/Special:Redirect/page/123"  # noqa: E501

    def test_get_url_missing_file(self):
        metadata_collector = self._create_metadata_collector(
            "Image NOT on Commons.jpeg"
        )
        page_class = type(metadata_collector._page)
        error = NoPageError(page=metadata_collector._page)
        page_class.latest_file_info = PropertyMock(side_effect=error)

        with pytest.raises(MissingMetadataError):
            metadata_collector.get_url()

    def test_get_name_from_filename(self):
        self.FilePage.return_value.pageid = "123"
        self._mock_response("M123", statements={"P6243": {"id": "Q456"}})
        self._mock_response("Q456", labels={})
        metadata_collector = self._create_metadata_collector(
            "Image on Commons.jpeg"
        )

        name = metadata_collector.get_name()

        assert name == "Image on Commons"

    def test_get_name_from_label(self):
        self.FilePage.return_value.pageid = "123"
        self._mock_response("M123", statements={"P6243": {"id": "Q456"}})
        self._mock_response("Q456", labels={"en": "Label"})
        metadata_collector = self._create_metadata_collector(
            "Image on Commons.jpeg"
        )
        name = metadata_collector.get_name()

        assert name == "Label"

    def test_get_name_from_title(self):
        self.FilePage.return_value.pageid = "123"
        metadata_collector = self._create_metadata_collector(
            "Image on Commons.jpeg"
        )
        self._mock_response("M123", statements={"P6243": {"id": "Q456"}})
        self._mock_response("Q456", claims={"P1476": {"text": "Title"}})
        name = metadata_collector.get_name()

        assert name == "Title"

    def test_get_license_for_image(self):
        self.FilePage.return_value.pageid = "123"
        metadata_collector = self._create_metadata_collector(
            "Image on Commons.jpeg"
        )
        self._mock_response("M123", statements={"P275": {"id": "Q456"}})
        self._mock_response(
            "Q456",
            claims={"P856": "https://creativecommons.org/licenses/by/1.0/"}
        )

        license = metadata_collector.get_license()

        assert license == "https://creativecommons.org/licenses/by/1.0/"

    def test_get_public_domain_for_image(self):
        self.FilePage.return_value.pageid = "123"
        metadata_collector = self._create_metadata_collector(
            "Image on Commons.jpeg"
        )
        self._mock_response("M123", statements={"P6216": {"id": "Q19652"}})

        license = metadata_collector.get_license()

        assert license == "https://creativecommons.org/publicdomain/mark/1.0/"

    def test_get_license_fails(self):
        self.FilePage.return_value.pageid = "123"
        metadata_collector = self._create_metadata_collector(
            "Image on Commons.jpeg"
        )
        self._mock_response("M123", statements={"P6243": {"id": "Q456"}})
        self._mock_response("Q456", statements={})

        with pytest.raises(MissingMetadataError):
            metadata_collector.get_license()

    def test_get_license_multiple_licenses(self):
        self.FilePage.return_value.pageid = "123"
        metadata_collector = self._create_metadata_collector(
            "Image on Commons.jpeg"
        )
        self._mock_response(
            "M123",
            statements={"P275": [{"id": "Q456"}, {"id": "Q789"}]}
        )
        self._mock_response(
            "Q456",
            claims={"P856": "https://creativecommons.org/licenses/by/1.0/"}
        )
        self._mock_response(
            "Q789",
            claims={"P856": "https://creativecommons.org/licenses/by/2.0/"}
        )

        license = metadata_collector.get_license()

        assert license == "https://creativecommons.org/licenses/by/1.0/"

    def test_get_license_multiple_licenses_some_invalid(self):
        self.FilePage.return_value.pageid = "123"
        metadata_collector = self._create_metadata_collector(
            "Image on Commons.jpeg"
        )
        self._mock_response(
            "M123",
            statements={"P275": [{"id": "Q456"}, {"id": "Q789"}]}
        )
        self._mock_response(
            "Q456",
            claims={"P856": "https://creativecommons.org/licenses/INVALID"}
        )
        self._mock_response(
            "Q789",
            claims={"P856": "https://creativecommons.org/licenses/by/1.0/"}
        )

        license = metadata_collector.get_license()

        assert license == "https://creativecommons.org/licenses/by/1.0/"

    def test_get_license_partial_match(self):
        self.FilePage.return_value.pageid = "123"
        metadata_collector = self._create_metadata_collector(
            "Image on Commons.jpeg"
        )
        self._mock_response("M123", statements={"P275": {"id": "Q456"}})
        self._mock_response(
            "Q456",
            claims={"P856": "https://creativecommons.org/licenses/by/1.0"}
        )

        license = metadata_collector.get_license()

        assert license == "https://creativecommons.org/licenses/by/1.0/"

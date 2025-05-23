from pywikibot import FilePage
from pywikibot.data.api import Request
from pywikibot.site import APISite


class MetadataCollector:
    def __init__(self, site: APISite, page: FilePage):
        self._site = site
        self._page = page

    def get_url(self) -> str:
        try:
            url = self._page.latest_file_info.descriptionshorturl
        except Exception:
            raise MissingMetadataError("Couldn't get URL.")

        return url

    def get_name(self) -> str:
        return (self._get_name_from_title()
                or self._get_name_from_label()
                or self._get_name_from_filename())

    def _get_name_from_label(self) -> str:
        entity = self._get_digital_representation()
        if entity is None:
            return None

        labels = entity.get("labels", {})
        label = labels.get("en", {}).get("value")
        return label

    def _get_digital_representation(self) -> dict:
        sdc = self._get_sdc()
        if sdc is None:
            return None

        # P6243 = "digital representation of"
        digital_representation = self._get_property(sdc, "P6243")
        if digital_representation is None:
            return None

        item = self._get_entity(digital_representation.get("id"))
        return item

    def _get_name_from_title(self) -> str:
        entity = self._get_digital_representation()
        if entity is None:
            return None

        # P1476 = "title"
        title = self._get_property(entity, "P1476")
        if title is None:
            return None

        return title.get("text")

    def _get_name_from_filename(self) -> str:
        filename = self._page.title(with_ns=False)
        # Remove the file extension.
        name_from_file = filename.rsplit(".", 1)[0]
        return name_from_file

    def _get_sdc(self) -> dict:
        sdc = self._get_entity(f"M{self._page.pageid}")
        return sdc

    def _get_entity(self, id_: str) -> dict:
        parameters = {
            "action": "wbgetentities",
            "ids": id_
        }
        request = Request(site=self._site, parameters=parameters)
        response = request.submit()
        item_id = list(response.get("entities", {}).keys())[0]
        entity = response.get("entities", {}).get(item_id)
        return entity

    def get_license(self) -> str:
        license = (self._get_license_for_depicted()
                   or self._get_license_for_image())
        if license is None:
            raise MissingMetadataError("Couldn't get license.")
        return license

    def _get_license_for_image(self) -> str:
        sdc = self._get_sdc()
        if sdc is None:
            return None

        return self._get_license_for_item(sdc)

    def _get_license_for_item(self, item) -> str:
        # P6216 = "copyright status"
        copyright_status = self._get_property(item, "P6216")
        if copyright_status is not None:
            copyright_item = copyright_status.get("id")
            if copyright_item == "Q19652":
                return "https://creativecommons.org/publicdomain/mark/1.0/"

        # P275 = "copyright license"
        license_property = self._get_property(item, "P275")
        if license_property is None:
            return None

        license_item_id = license_property.get("id")
        license_item = self._get_entity(license_item_id)
        # P856 = "official website"
        license_url = self._get_property(license_item, "P856")

        return license_url

    def _get_license_for_depicted(self) -> str:
        depicted = self._get_digital_representation()
        if depicted is None:
            return None

        return self._get_license_for_item(depicted)

    def _get_property(self, entity: dict, property_name: str):
        property_ = (
            entity.get("claims", {})
            or entity.get("statements", {})
        ).get(property_name, [None])[0]

        if property_ is None:
            return None

        value = property_.get("mainsnak", {}).get("datavalue", {}).get("value")
        return value


class MissingMetadataError(Exception):
    pass

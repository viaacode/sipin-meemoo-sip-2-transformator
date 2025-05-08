from typing import Any

from lxml import etree
from sippy.utils import EDTF_level1

from app.mets import METS
from app.utils import (
    parse_lang_str,
    xpath_text,
)


def parse_descriptive(mets: METS) -> dict[str, Any]:
    if mets.descriptive_metadata is None:
        return {}

    metadata_xml = etree.parse(mets.descriptive_metadata).getroot()

    alternative = parse_lang_str(metadata_xml, "dcterms:alternative")
    alternative = [alternative] if alternative else []

    descriptive = {
        "name": parse_lang_str(metadata_xml, "dcterms:title"),
        "alternative_name": alternative,
        # TODO: fix datetime
        # "available": xpath_optional_text(metadata_xml, "dcterms:available/text()"),
        # "description": parse_lang_str(metadata_xml, "dcterms:description"),
        # "abstract": parse_lang_str(metadata_xml, "dcterms:abstract"),
        "date_created": EDTF_level1(
            value=xpath_text(metadata_xml, "dcterms:created/text()")
        ),
        # "date_published": EDTF_level1(
        #     value=xpath_text(metadata_xml, "dcterms:issued/text()")
        # ),
        # "publisher"
        # "contributor"
        # "creator"
        # "spatial"
        # "temporal"
        # "subject"
        # "language"
        # "license"
        # "rightsholder"
        # "rights"
        # "type"
        # "height"
        # "width"
        # "depth"
        # "weight"
        # "artmedium"
        # "artform"
        # "schema_is_part_of"
    }

    return descriptive

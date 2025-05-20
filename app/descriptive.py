from typing import Any, Literal

import dateutil.parser
from lxml import etree
from lxml.etree import _Element
from sippy.descriptive import Concept, Person, Place, QuantitativeValue, Role, Thing
from sippy.utils import DateTime, EDTF_level1, Float, LangStr

from app.mets import METS
from app.utils import (
    ParseException,
    xpath_element_list,
    xpath_lang_str,
    xpath_optional_element,
    xpath_optional_lang_str,
    xpath_optional_text,
    xpath_text,
    xpath_text_list,
)


def parse_role(
    dcterms: _Element, role_type: Literal["creator", "publisher", "contributor"]
) -> list[Role]:

    match role_type:
        case "creator":
            default_role_name = "Maker"
        case "publisher":
            default_role_name = "Publisher"
        case "contributor":
            default_role_name = "Bijdrager"

    roles_xml = xpath_element_list(dcterms, f"schema:{role_type}") + xpath_element_list(
        dcterms, f"dcterms:{role_type}"
    )

    roles = []
    for role_xml in roles_xml:
        role_name = xpath_optional_text(role_xml, "@schema:roleName")
        name = xpath_text(role_xml, "schema:name/text()")
        member = Thing(
            name=LangStr(nl=name),
        )

        birth_date = xpath_optional_text(role_xml, "schema:birthDate")
        death_date = xpath_optional_text(role_xml, "schema:deathDate")

        if birth_date or death_date:
            member = Person(
                name=LangStr(nl=name),
                birth_date=EDTF_level1(value=birth_date) if birth_date else None,
                death_date=EDTF_level1(value=death_date) if death_date else None,
            )

        roles.append(
            Role(
                role_name=role_name if role_name else default_role_name,
                publisher=member if role_type == "publisher" else None,
                creator=member if role_type == "creator" else None,
                contributor=member if role_type == "contributor" else None,
            )
        )

    return roles


def unit_text_to_code(text: str) -> str:
    match text:
        case "mm":
            return "MMT"
        case "cm":
            return "CMT"
        case "m":
            return "MTR"
        case "kg":
            return "KGM"

    raise ParseException(f"Unknown unit text: {text}")


def parse_descriptive(mets: METS) -> dict[str, Any]:

    if mets.descriptive_metadata is None:
        raise ParseException("Package must have descriptive metdata")

    dcterms = etree.parse(mets.descriptive_metadata).getroot()
    alternative = xpath_optional_lang_str(dcterms, "dcterms:alternative")

    available = xpath_optional_text(dcterms, "dcterms:available/text()")
    available = dateutil.parser.parse(available) if available else None

    issued = xpath_optional_text(dcterms, "dcterms:issued/text()")

    spatial = xpath_text_list(dcterms, "dcterms:spatial")
    spatial = [Place(name=LangStr(nl=s)) for s in spatial]

    copyright_holder = xpath_optional_text(dcterms, "dcterms:rightsHolder/text()")

    height_value = xpath_optional_text(dcterms, "schema:height/schema:value/text()")
    height_unit_text = xpath_optional_text(
        dcterms, "schema:height/schema:unitText/text()"
    )
    depth_value = xpath_optional_text(dcterms, "schema:depth/schema:value/text()")
    depth_unit_text = xpath_optional_text(
        dcterms, "schema:depth/schema:unitText/text()"
    )
    width_value = xpath_optional_text(dcterms, "schema:width/schema:value/text()")
    width_unit_text = xpath_optional_text(
        dcterms, "schema:width/schema:unitText/text()"
    )
    weight_value = xpath_optional_text(dcterms, "schema:weight/schema:value/text()")
    weight_unit_text = xpath_optional_text(
        dcterms, "schema:weight/schema:unitText/text()"
    )

    return {
        "name": xpath_lang_str(dcterms, "dcterms:title"),
        "alternative_name": [alternative] if alternative else [],
        # TODO: dcterms:extend
        "available": DateTime(value=available) if available else None,
        "description": xpath_lang_str(dcterms, "dcterms:description"),
        "abstract": xpath_optional_lang_str(dcterms, "dcterms:abstract"),
        "date_created": EDTF_level1(
            value=xpath_text(dcterms, "dcterms:created/text()")
        ),
        "date_published": EDTF_level1(value=issued) if issued else None,
        "publisher": parse_role(dcterms, "publisher"),
        "contributor": parse_role(dcterms, "contributor"),
        "creator": parse_role(dcterms, "creator"),
        "spatial": spatial,
        # "temporal": TODO
        "keywords": (
            [keywords]
            if (keywords := xpath_optional_lang_str(dcterms, "dcterms:subject"))
            else []
        ),
        "in_language": xpath_text_list(dcterms, "dcterms:language"),
        # TODO: is this simple mapping for licenses ok?
        "license": [
            Concept(id="https://data.hetarchief.be/id/license/" + l)
            for l in xpath_text_list(dcterms, "dcterms:license/text()")
        ],
        "copyright_holder": (
            [Thing(name=LangStr(nl=copyright_holder))] if (copyright_holder) else []
        ),
        "rights": (
            [LangStr(nl=rights)]
            if (rights := xpath_optional_text(dcterms, "dcterms:rights/text()"))
            else []
        ),
        # "type"
        "height": (
            QuantitativeValue(
                value=Float(value=float(height_value)),
                unit_code=unit_text_to_code(height_unit_text),
                unit_text=height_unit_text,
            )
            if height_value and height_unit_text
            else None
        ),
        "width": (
            QuantitativeValue(
                value=Float(value=float(width_value)),
                unit_code=unit_text_to_code(width_unit_text),
                unit_text=width_unit_text,
            )
            if width_value and width_unit_text
            else None
        ),
        "depth": (
            QuantitativeValue(
                value=Float(value=float(depth_value)),
                unit_code=unit_text_to_code(depth_unit_text),
                unit_text=depth_unit_text,
            )
            if depth_value and depth_unit_text
            else None
        ),
        "weight": (
            QuantitativeValue(
                value=Float(value=float(weight_value)),
                unit_code=unit_text_to_code(weight_unit_text),
                unit_text=weight_unit_text,
            )
            if weight_value and weight_unit_text
            else None
        ),
        # "art_medium":
        # "artform"
        # "schema_is_part_of"
    }

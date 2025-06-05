from datetime import datetime
from typing import Self, Any
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from pathlib import Path

from pydantic import BaseModel

import sippy

from . import schema
from .xml_lang import LangStr
from .sippify import Sippify

from ..parse import Parser

EDTF = str


class DCPlusSchema(BaseModel):
    # basic profile
    title: LangStr
    alternative: LangStr | None
    # TODO: extend
    available: datetime | None
    description: LangStr
    abstract: LangStr | None
    created: EDTF
    issued: EDTF | None
    publisher: list[schema.Publisher]
    creator: list[schema.Creator]
    contributor: list[schema.Contributor]
    spatial: list[str]
    temporal: list[str]
    subject: LangStr | None
    language: list[str]
    license: list[str]
    rights_holder: str | None
    rights: LangStr | None
    format: str
    height: schema.Height | None
    width: schema.Width | None
    depth: schema.Depth | None
    weight: schema.Weight | None
    art_medium: LangStr | None
    artform: LangStr | None
    is_part_of: list[schema.AnyCreativeWork | schema.BroadcastEvent]

    # film profile
    country_of_origin: str | None
    credit_text: list[str]
    genre: str | None

    @classmethod
    def from_xml(cls, path: str | Path) -> Self:
        root = ElementTree.parse(path).getroot()
        return cls.from_xml_tree(root)

    @classmethod
    def from_xml_tree(cls, root: Element) -> Self:
        creators = Parser.element_list(root, "schema:creator")
        creators += Parser.element_list(root, "dcterms:creator")
        publishers = Parser.element_list(root, "schema:publisher")
        publishers += Parser.element_list(root, "dcterms:publisher")
        contributors = Parser.element_list(root, "schema:contributor")
        contributors += Parser.element_list(root, "dcterms:contributor")

        is_part_of = [
            schema.parse_is_part_of(el)
            for el in Parser.element_list(root, "schema:isPartOf")
        ]

        return cls(
            title=LangStr.new(root, "dcterms:title"),
            alternative=LangStr.optional(root, "dcterms:alternative"),
            available=Parser.optional_datetime(root, "dcterms:available"),
            description=LangStr.new(root, "dcterms:description"),
            abstract=LangStr.optional(root, "dcterms:abstract"),
            created=Parser.text(root, "dcterms:created"),
            issued=Parser.optional_text(root, "dcterms:issued"),
            spatial=Parser.text_list(root, "dcterms:spatial"),
            temporal=Parser.text_list(root, "dcterms:temporal"),
            subject=LangStr.optional(root, "dcterms:subject"),
            language=Parser.text_list(root, "dcterms:language"),
            license=Parser.text_list(root, "dcterms:license"),
            rights_holder=Parser.optional_text(root, "dcterms:rightsHolder"),
            rights=LangStr.optional(root, "dcterms:rights"),
            format=Parser.text(root, "dcterms:format"),
            creator=[schema.Creator.from_xml_tree(el) for el in creators],
            publisher=[schema.Publisher.from_xml_tree(el) for el in publishers],
            contributor=[schema.Contributor.from_xml_tree(el) for el in contributors],
            height=schema.Height.from_xml_tree(root, "schema:height"),
            width=schema.Width.from_xml_tree(root, "schema:width"),
            depth=schema.Depth.from_xml_tree(root, "schema:depth"),
            weight=schema.Weight.from_xml_tree(root, "schema:weight"),
            art_medium=LangStr.optional(root, "dcterms:artMedium"),
            artform=LangStr.optional(root, "dcterms:artform"),
            is_part_of=is_part_of,
            country_of_origin=Parser.optional_text(root, "schema:countryOfOrigin"),
            credit_text=Parser.text_list(root, "schema:creditText"),
            genre=Parser.optional_text(root, "schema:genre"),
        )


def parse_dc_schema(path: Path) -> dict[str, Any]:
    desc = DCPlusSchema.from_xml(path)

    return {
        "name": Sippify.lang_str(desc.title),
        "alternative_name": [Sippify.lang_str(desc.alternative)],
        # # TODO: dcterms:extend
        "available": (sippy.DateTime(value=desc.available) if desc.available else None),
        "description": Sippify.lang_str(desc.description),
        "abstract": Sippify.lang_str(desc.abstract),
        "date_created": sippy.EDTF_level1(value=desc.created),
        "date_published": (
            sippy.EDTF_level1(value=desc.issued) if desc.issued else None
        ),
        "publisher": [Sippify.publisher(publisher) for publisher in desc.publisher],
        "creator": [Sippify.creator(creator) for creator in desc.creator],
        "contributor": [
            Sippify.contributor(contributor) for contributor in desc.contributor
        ],
        "spatial": [sippy.Place(name=sippy.LangStr(nl=s)) for s in desc.spatial],
        "temporal": [sippy.LangStr(nl=t) for t in desc.temporal],
        "keywords": [Sippify.lang_str(desc.subject)] if desc.subject else [],
        "in_language": desc.language,
        # # TODO: is this simple mapping for licenses ok?
        "license": [
            sippy.Concept(id="https://data.hetarchief.be/id/license/" + l)
            for l in desc.license
        ],
        "copyright_holder": (
            [sippy.Thing(name=sippy.LangStr(nl=desc.rights_holder))]
            if desc.rights_holder
            else []
        ),
        "rights": ([Sippify.lang_str(desc.rights)] if desc.rights else []),
        "format": sippy.String(value=desc.format),
        "height": Sippify.quantitive_value(desc.height),
        "width": Sippify.quantitive_value(desc.width),
        "depth": Sippify.quantitive_value(desc.depth),
        "weight": Sippify.quantitive_value(desc.weight),
        "art_medium": ([Sippify.lang_str(desc.art_medium)] if desc.art_medium else []),
        "artform": [Sippify.lang_str(desc.artform)] if desc.artform else [],
        "schema_is_part_of": [Sippify.creative_work(cw) for cw in desc.is_part_of],
        "credit_text": [sippy.LangStr(nl=s) for s in desc.credit_text],
    }

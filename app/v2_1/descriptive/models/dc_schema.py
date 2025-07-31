import typing
from typing import Self, Literal, TextIO
from xml.etree.ElementTree import Element
import xml.etree.ElementTree as ET
from pathlib import Path
from ...namespaces import schema, dcterms, xsi

from pydantic import BaseModel

from .xml_lang import XMLLang
from ...utils import ParseException, Parser


EDTF = str


class _Role(BaseModel):
    role_name: str | None
    name: XMLLang
    birth_date: str | None
    death_date: str | None

    @classmethod
    def from_xml_tree(cls, root: Element) -> Self:
        return cls(
            name=XMLLang.new(root, schema.name),
            role_name=root.get(schema.roleName),
            birth_date=Parser.optional_text(root, schema.birthDate),
            death_date=Parser.optional_text(root, schema.deathDate),
        )


class Creator(_Role):
    pass


class Publisher(_Role):
    pass


class Contributor(_Role):
    pass


UnitCode = Literal["MMT", "CMT", "MTR", "KGM"]
UnitText = Literal["mm", "cm", "m", "kg"]


class _Measurement(BaseModel):
    value: str
    unit_code: UnitCode | None
    unit_text: UnitText

    @classmethod
    def from_xml_tree(cls, root: Element, path: str) -> Self | None:
        element = root.find(path)
        if element is None:
            return None
        value = Parser.text(element, schema.value)
        unit_code = Parser.optional_text(element, schema.unitCode)
        unit_text = Parser.text(element, schema.unitText)

        if unit_code is not None and unit_code not in ("MMT", "CMT", "MTR", "KGM"):
            raise ParseException(
                f"Unit code should be one of {typing.get_args(UnitCode)}"
            )
        if unit_text is not None and unit_text not in ("mm", "cm", "m", "kg"):
            raise ParseException(
                f"Unit text should be one of {typing.get_args(UnitText)}"
            )

        return cls(
            value=value,
            unit_code=unit_code,
            unit_text=unit_text,
        )


class Height(_Measurement):
    pass


class Width(_Measurement):
    pass


class Depth(_Measurement):
    pass


class Weight(_Measurement):
    pass


CreativeWorkType = Literal[
    schema.Episode,
    schema.ArchiveComponent,
    schema.CreativeWorkSeries,
    schema.CreativeWorkSeason,
]

EventTypes = Literal[schema.BroadcastEvent]


class Episode(BaseModel):
    name: XMLLang

    @classmethod
    def from_xml_tree(cls, root: Element) -> Self:
        return cls(name=XMLLang.new(root, schema.name))


class ArchiveComponent(BaseModel):
    name: XMLLang

    @classmethod
    def from_xml_tree(cls, root: Element) -> Self:
        return cls(name=XMLLang.new(root, schema.name))


class CreativeWorkSeries(BaseModel):
    name: XMLLang
    position: int | None
    has_part: XMLLang

    @classmethod
    def from_xml_tree(cls, root: Element) -> Self:
        position = Parser.optional_text(root, schema.position)
        has_part = Parser.element(root, schema.hasPart)
        return cls(
            name=XMLLang.new(root, schema.name),
            position=int(position) if position else None,
            has_part=XMLLang.new(has_part, schema.name),
        )


class CreativeWorkSeason(BaseModel):
    name: XMLLang
    season_number: int | None

    @classmethod
    def from_xml_tree(cls, root: Element) -> Self:
        season_number = Parser.optional_text(root, schema.seasonNumber)
        return cls(
            name=XMLLang.new(root, schema.name),
            season_number=int(season_number) if season_number else None,
        )


class BroadcastEvent(BaseModel):
    name: XMLLang

    @classmethod
    def from_xml_tree(cls, root: Element) -> Self:
        return cls(name=XMLLang.new(root, schema.name))


AnyCreativeWork = Episode | ArchiveComponent | CreativeWorkSeries | CreativeWorkSeason


def parse_is_part_of(root: Element) -> AnyCreativeWork | BroadcastEvent:
    type = root.get(xsi.type)

    valid_types = typing.get_args(CreativeWorkType) + typing.get_args(EventTypes)
    if type not in valid_types:
        raise ParseException(f"schema:isPartOf must be one of {valid_types}")

    match type:
        case schema.Episode:
            return Episode.from_xml_tree(root)
        case schema.ArchiveComponent:
            return ArchiveComponent.from_xml_tree(root)
        case schema.CreativeWorkSeries:
            return CreativeWorkSeries.from_xml_tree(root)
        case schema.CreativeWorkSeason:
            return CreativeWorkSeason.from_xml_tree(root)
        case schema.BroadcastEvent:
            return BroadcastEvent.from_xml_tree(root)
        case _:
            raise AssertionError("CreativeWorkType or EventTypes are not complete")


xsd_duration = str
xsd_timedelta = str


class DCPlusSchema(BaseModel):
    # basic profile
    identifier: str
    title: XMLLang
    alternative: XMLLang | None
    extent: xsd_duration | None
    available: xsd_timedelta | None
    description: XMLLang
    abstract: XMLLang | None
    created: EDTF
    issued: EDTF | None
    publisher: list[Publisher]
    creator: list[Creator]
    contributor: list[Contributor]
    spatial: list[str]
    temporal: XMLLang | None
    subject: XMLLang | None
    language: list[str]
    license: list[str]
    rights_holder: XMLLang | None
    rights: XMLLang | None
    type: str
    format: str
    height: Height | None
    width: Width | None
    depth: Depth | None
    weight: Weight | None
    art_medium: XMLLang | None
    artform: XMLLang | None
    is_part_of: list[AnyCreativeWork | BroadcastEvent]

    credit_text: XMLLang | None
    genre: XMLLang | None

    @classmethod
    def from_xml(cls, path: str | Path) -> Self:
        return cls.from_xml_tree(parse_xml(path))

    @classmethod
    def from_xml_tree(cls, root: Element) -> Self:
        creators = Parser.element_list(root, schema.creator)
        creators += Parser.element_list(root, dcterms.creator)
        publishers = Parser.element_list(root, schema.publisher)
        publishers += Parser.element_list(root, dcterms.publisher)
        contributors = Parser.element_list(root, schema.contributor)
        contributors += Parser.element_list(root, dcterms.contributor)

        is_part_of = [
            parse_is_part_of(el) for el in Parser.element_list(root, schema.isPartOf)
        ]

        return cls(
            identifier=Parser.text(root, dcterms.identifier),
            title=XMLLang.new(root, dcterms.title),
            alternative=XMLLang.optional(root, dcterms.alternative),
            extent=Parser.optional_text(root, dcterms.extent),
            available=Parser.optional_text(root, dcterms.available),
            description=XMLLang.new(root, dcterms.description),
            abstract=XMLLang.optional(root, dcterms.abstract),
            created=Parser.text(root, dcterms.created),
            issued=Parser.optional_text(root, dcterms.issued),
            spatial=Parser.text_list(root, dcterms.spatial),
            temporal=XMLLang.optional(root, dcterms.temporal),
            subject=XMLLang.optional(root, dcterms.subject),
            language=Parser.text_list(root, dcterms.language),
            license=Parser.text_list(root, dcterms.license),
            rights_holder=XMLLang.optional(root, dcterms.rightsHolder),
            rights=XMLLang.optional(root, dcterms.rights),
            type=Parser.text(root, dcterms.type),
            format=Parser.text(root, dcterms.format),
            creator=[Creator.from_xml_tree(el) for el in creators],
            publisher=[Publisher.from_xml_tree(el) for el in publishers],
            contributor=[Contributor.from_xml_tree(el) for el in contributors],
            height=Height.from_xml_tree(root, schema.height),
            width=Width.from_xml_tree(root, schema.width),
            depth=Depth.from_xml_tree(root, schema.depth),
            weight=Weight.from_xml_tree(root, schema.weight),
            art_medium=XMLLang.optional(root, schema.artMedium),
            artform=XMLLang.optional(root, schema.artform),
            is_part_of=is_part_of,
            credit_text=XMLLang.optional(root, schema.creditText),
            genre=XMLLang.optional(root, schema.genre),
        )


def expand_attribute_qnames(
    element: Element, document_namespaces: dict[str, str]
) -> Element:
    """
    Certain attributes may have a prefixed value e.g. xsi:type="schema:Episode".
    Expand the prefixed attribute value to its full qualified name e.g. "{https://schema.org/}Episode"
    """

    for k, v in element.attrib.items():
        if k == xsi.type:
            element.attrib[k] = expand_qname(v, document_namespaces)

    for child in element:
        _ = expand_attribute_qnames(child, document_namespaces)

    return element


def parse_xml(source: str | Path | TextIO):
    document_namespaces = get_document_namespaces(source)
    if not isinstance(source, (str, Path)):
        source.seek(0)
    root = ET.parse(source).getroot()
    return expand_attribute_qnames(root, document_namespaces)


def expand_qname(name: str, document_namespaces: dict[str, str]) -> str:
    """
    Expand a prefixed qualified name to its fully qualified name.
    E.g. "schema:Episode" is expanded to "{https://schema.org/}Episode"
    """

    if ":" not in name:
        return name

    splitted_qname = name.split(":", 1)
    prefix = splitted_qname[0]
    local = splitted_qname[1]
    prefix_iri = document_namespaces[prefix]

    return "{" + prefix_iri + "}" + local


def get_document_namespaces(source: str | Path | TextIO) -> dict[str, str]:
    document_namespaces = [
        ns_tuple for _, ns_tuple in ET.iterparse(source, events=["start-ns"])
    ]
    return dict(typing.cast(list[tuple[str, str]], document_namespaces))

from datetime import datetime
import typing
from typing import Self, Literal

from pydantic import BaseModel
from lxml import etree
from lxml.etree import _Element
import dateutil.parser

from app.utils import ParseException, ns

EDTF = str


class XMLLangStr(BaseModel):
    content: dict[str, str]

    @classmethod
    def new(cls, root: _Element, path: str) -> Self:
        lang_str = cls.optional(root, path)
        if lang_str is None:
            raise ParseException(f"Cannot create lang string from elements at {path}")
        return lang_str

    @classmethod
    def optional(cls, root: _Element, path: str) -> Self | None:
        elements = root.findall(path, namespaces=ns)
        if len(elements) == 0:
            return None

        content = {}
        for element in elements:
            value = element.text
            lang = element.get("{http://www.w3.org/XML/1998/namespace}lang")
            if lang is None:
                raise ParseException(
                    f"No `xml:lang` attribute found on lang string {path}."
                )
            content |= {lang: value}
        return cls(content=content)


class SIPRole(BaseModel):
    role_name: str | None
    name: str
    birth_date: str | None
    death_date: str | None

    @classmethod
    def new(cls, root: _Element) -> Self:
        return cls(
            name=parse_text(root, "schema:name"),
            role_name=root.get("{https://schema.org/}roleName"),
            birth_date=parse_optional_text(root, "schema:birthDate"),
            death_date=parse_optional_text(root, "schema:deathDate"),
        )


UnitCode = Literal["MMT", "CMT", "MTR", "KGM"]
UnitText = Literal["mm", "cm", "m", "kg"]


class Measurement(BaseModel):
    value: float
    unit_code: UnitCode | None
    unit_text: UnitText

    @classmethod
    def new(cls, root: _Element, path: str) -> Self | None:
        element = root.find(path, namespaces=ns)
        if element is None:
            return None
        value = element.findtext("schema:value", namespaces=ns)
        unit_code = parse_optional_text(element, "schema:unitCode")
        unit_text = parse_text(element, "schema:unitText")

        if value is None:
            raise ParseException(
                "height, width, depth and weight elements should have a schema:value"
            )
        if unit_code is not None and unit_code not in typing.get_args(UnitCode):
            raise ParseException(
                f"Unit code should be one of {typing.get_args(UnitCode)}"
            )
        if unit_code is not None:
            unit_code = typing.cast(UnitCode, unit_code)
        if unit_text is not None and unit_text not in typing.get_args(UnitText):
            raise ParseException(
                f"Unit text should be one of {typing.get_args(UnitText)}"
            )
        if unit_text is not None:
            unit_text = typing.cast(UnitText, unit_text)

        return cls(
            value=float(value),
            unit_code=unit_code,
            unit_text=unit_text,
        )


CreativeWorkType = Literal[
    "schema:Episode",
    "schema:ArchiveComponent",
    "schema:CreativeWorkSeries",
    "schema:CreativeWorkSeason",
    "schema:BroadcastEvent",
]


class SIPEpisode(BaseModel):
    type: Literal["schema:Episode"]
    name: str


class SIPArchiveComponent(BaseModel):
    type: Literal["schema:ArchiveComponent"]
    name: str


class SIPCreativeWorkSeries(BaseModel):
    type: Literal["schema:CreativeWorkSeries"]
    name: str
    position: int | None
    has_parts: list[str]


class SIPCreativeWorkSeason(BaseModel):
    type: Literal["schema:CreativeWorkSeason"]
    name: str
    season_number: int | None


class SIPBroadcastEvent(BaseModel):
    type: Literal["schema:BroadcastEvent"]
    name: str


SIPAnyCreativeWork = (
    SIPEpisode | SIPArchiveComponent | SIPCreativeWorkSeries | SIPCreativeWorkSeason
)


def parse_is_part_of(root: _Element) -> SIPAnyCreativeWork | SIPBroadcastEvent:
    type = root.get("xsi:type")
    if type not in typing.get_args(CreativeWorkType):
        raise ParseException(
            f"schema:isPartOf must be one of {typing.get_args(CreativeWorkType)}"
        )
    type = typing.cast(CreativeWorkType, type)
    name = parse_text(root, "schema:name")

    match type:
        case "schema:Episode":
            return SIPEpisode(type=type, name=name)
        case "schema:ArchiveComponent":
            return SIPArchiveComponent(type=type, name=name)
        case "schema:CreativeWorkSeries":
            position = parse_optional_text(root, "schema:position")
            return SIPCreativeWorkSeries(
                type=type,
                name=name,
                position=int(position) if position else None,
                has_parts=parse_text_list(root, "schema:hasPart/schema:name"),
            )
        case "schema:CreativeWorkSeason":
            season_number = parse_optional_text(root, "schema:seasonNumber")
            return SIPCreativeWorkSeason(
                type=type,
                name=name,
                season_number=int(season_number) if season_number else None,
            )
        case "schema:BroadcastEvent":
            return SIPBroadcastEvent(type=type, name=name)


class DCSchema(BaseModel):
    # basic profile
    title: XMLLangStr
    alternative: XMLLangStr | None
    # TODO: extend
    available: datetime | None
    description: XMLLangStr
    abstract: XMLLangStr | None
    created: EDTF
    issued: EDTF | None
    publisher: list[SIPRole]
    creator: list[SIPRole]
    contributor: list[SIPRole]
    spatial: list[str]
    temporal: list[str]
    subject: XMLLangStr | None
    language: list[str]
    license: list[str]
    rights_holder: str | None
    rights: XMLLangStr | None
    format: str
    height: Measurement | None
    width: Measurement | None
    depth: Measurement | None
    weight: Measurement | None
    art_medium: XMLLangStr | None
    artform: XMLLangStr | None
    is_part_of: list[SIPAnyCreativeWork | SIPBroadcastEvent]

    # film profile
    country_of_origin: str | None
    credit_text: list[str]
    genre: str | None

    @classmethod
    def from_xml(cls, path: str) -> Self:
        root = etree.parse(path).getroot()
        return cls.validate_dc_schema(root)

    @classmethod
    def validate_dc_schema(cls, root: _Element) -> Self:
        creators = parse_element_list(root, "schema:creator")
        creators += parse_element_list(root, "dcterms:creator")
        publishers = parse_element_list(root, "schema:publisher")
        publishers += parse_element_list(root, "dcterms:publisher")
        contributors = parse_element_list(root, "schema:contributor")
        contributors += parse_element_list(root, "dcterms:contributor")

        is_part_of = [
            parse_is_part_of(el)
            for el in root.findall("schema:isPartOf", namespaces=ns)
        ]

        return cls(
            title=XMLLangStr.new(root, "dcterms:title"),
            alternative=XMLLangStr.optional(root, "dcterms:alternative"),
            available=parse_optional_datetime(root, "dcterms:available"),
            description=XMLLangStr.new(root, "dcterms:description"),
            abstract=XMLLangStr.optional(root, "dcterms:abstract"),
            created=parse_text(root, "dcterms:created"),
            issued=parse_optional_text(root, "dcterms:issued"),
            spatial=parse_text_list(root, "dcterms:spatial"),
            temporal=parse_text_list(root, "dcterms:temporal"),
            subject=XMLLangStr.optional(root, "dcterms:subject"),
            language=parse_text_list(root, "dcterms:language"),
            license=parse_text_list(root, "dcterms:license"),
            rights_holder=parse_optional_text(root, "dcterms:rightsHolder"),
            rights=XMLLangStr.optional(root, "dcterms:rights"),
            format=parse_text(root, "dcterms:format"),
            creator=[SIPRole.new(el) for el in creators],
            publisher=[SIPRole.new(el) for el in publishers],
            contributor=[SIPRole.new(el) for el in contributors],
            height=Measurement.new(root, "schema:height"),
            width=Measurement.new(root, "schema:width"),
            depth=Measurement.new(root, "schema:depth"),
            weight=Measurement.new(root, "schema:weight"),
            art_medium=XMLLangStr.optional(root, "dcterms:artMedium"),
            artform=XMLLangStr.optional(root, "dcterms:artform"),
            is_part_of=is_part_of,
            country_of_origin=parse_optional_text(root, "schema:countryOfOrigin"),
            credit_text=parse_text_list(root, "schema:creditText"),
            genre=parse_optional_text(root, "schema:genre"),
        )


def parse_text(root: _Element, path: str) -> str:
    text = root.findtext(path, namespaces=ns)
    if text is None:
        raise ParseException(f"No element found at {path}")
    return text


def parse_optional_text(root: _Element, path: str) -> str | None:
    return root.findtext(path, namespaces=ns)


def parse_text_list(root: _Element, path: str) -> list[str]:
    return [el.text for el in root.findall(path, namespaces=ns) if el.text]


def parse_element_list(root: _Element, path: str) -> list[_Element]:
    return root.findall(path, namespaces=ns)


def parse_optional_datetime(root: _Element, path: str) -> datetime | None:
    element = root.find(path, namespaces=ns)
    if element is None:
        return None
    if element.text is None:
        return None
    return dateutil.parser.parse(element.text)

import typing
from typing import Self, Literal
from xml.etree.ElementTree import Element

from pydantic import BaseModel

from ..parse import Parser
from ..utils import ParseException


class _Role(BaseModel):
    role_name: str | None
    name: str
    birth_date: str | None
    death_date: str | None

    @classmethod
    def from_xml_tree(cls, root: Element) -> Self:
        return cls(
            name=Parser.text(root, "schema:name"),
            role_name=root.get("schema:roleName"),
            birth_date=Parser.optional_text(root, "schema:birthDate"),
            death_date=Parser.optional_text(root, "schema:deathDate"),
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
    value: float
    unit_code: UnitCode | None
    unit_text: UnitText

    @classmethod
    def from_xml_tree(cls, root: Element, path: str) -> Self | None:
        element = root.find(path)
        if element is None:
            return None
        value = Parser.text(element, "schema:value")
        unit_code = Parser.optional_text(element, "schema:unitCode")
        unit_text = Parser.text(element, "schema:unitText")

        if unit_code is not None and unit_code not in ("MMT", "CMT", "MTR", "KGM"):
            raise ParseException(
                f"Unit code should be one of {typing.get_args(UnitCode)}"
            )
        if unit_text is not None and unit_text not in ("mm", "cm", "m", "kg"):
            raise ParseException(
                f"Unit text should be one of {typing.get_args(UnitText)}"
            )

        return cls(
            value=float(value),
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
    "schema:Episode",
    "schema:ArchiveComponent",
    "schema:CreativeWorkSeries",
    "schema:CreativeWorkSeason",
    "schema:BroadcastEvent",
]


class Episode(BaseModel):
    type: Literal["schema:Episode"]
    name: str

    @classmethod
    def from_xml_tree(cls, root: Element) -> Self:
        type = root.get("xsi:type")
        if type != "schema:Episode":
            raise ParseException()

        return cls(type=type, name=Parser.text(root, "schema:name"))


class ArchiveComponent(BaseModel):
    type: Literal["schema:ArchiveComponent"]
    name: str

    @classmethod
    def from_xml_tree(cls, root: Element) -> Self:
        type = root.get("xsi:type")
        if type != "schema:ArchiveComponent":
            raise ParseException()

        return cls(type=type, name=Parser.text(root, "schema:name"))


class CreativeWorkSeries(BaseModel):
    type: Literal["schema:CreativeWorkSeries"]
    name: str
    position: int | None
    has_parts: list[str]

    @classmethod
    def from_xml_tree(cls, root: Element) -> Self:
        position = Parser.optional_text(root, "schema:position")
        type = root.get("xsi:type")
        if type != "schema:CreativeWorkSeries":
            raise ParseException()

        return cls(
            type=type,
            name=Parser.text(root, "schema:name"),
            position=int(position) if position else None,
            has_parts=Parser.text_list(root, "schema:hasPart/schema:name"),
        )


class CreativeWorkSeason(BaseModel):
    type: Literal["schema:CreativeWorkSeason"]
    name: str
    season_number: int | None

    @classmethod
    def from_xml_tree(cls, root: Element) -> Self:
        season_number = Parser.optional_text(root, "schema:seasonNumber")
        type = root.get("xsi:type")
        if type != "schema:CreativeWorkSeason":
            raise ParseException()

        return cls(
            type=type,
            name=Parser.text(root, "schema:name"),
            season_number=int(season_number) if season_number else None,
        )


class BroadcastEvent(BaseModel):
    type: Literal["schema:BroadcastEvent"]
    name: str

    @classmethod
    def from_xml_tree(cls, root: Element) -> Self:
        type = root.get("xsi:type")
        if type != "schema:BroadcastEvent":
            raise ParseException()

        return cls(type=type, name=Parser.text(root, "schema:name"))


AnyCreativeWork = Episode | ArchiveComponent | CreativeWorkSeries | CreativeWorkSeason


def parse_is_part_of(root: Element) -> AnyCreativeWork | BroadcastEvent:
    type = root.get("xsi:type")
    # TODO: expand qname
    # TODO: should this use get_args?
    if type not in (
        "schema:Episode",
        "schema:ArchiveComponent",
        "schema:CreativeWorkSeries",
        "schema:CreativeWorkSeason",
        "schema:BroadcastEvent",
    ):
        raise ParseException(
            f"schema:isPartOf must be one of {typing.get_args(CreativeWorkType)}"
        )

    match type:
        case "schema:Episode":
            return Episode.from_xml_tree(root)
        case "schema:ArchiveComponent":
            return ArchiveComponent.from_xml_tree(root)
        case "schema:CreativeWorkSeries":
            return CreativeWorkSeries.from_xml_tree(root)
        case "schema:CreativeWorkSeason":
            return CreativeWorkSeason.from_xml_tree(root)
        case "schema:BroadcastEvent":
            return BroadcastEvent.from_xml_tree(root)

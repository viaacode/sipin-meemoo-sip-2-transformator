from typing import Any, Literal

from sippy.descriptive import (
    AnyCreativeWork,
    ArchiveComponent,
    BroadcastEvent,
    Concept,
    CreativeWorkSeason,
    CreativeWorkSeries,
    Episode,
    Person,
    Place,
    QuantitativeValue,
    Role,
    Thing,
)
from sippy.utils import DateTime, EDTF_level1, Float, LangStr, String

from app.dc_schema import (
    DCSchema,
    SIPRole,
    Measurement,
    XMLLangStr,
    SIPAnyCreativeWork,
    SIPEpisode,
    SIPArchiveComponent,
    SIPBroadcastEvent,
    SIPCreativeWorkSeries,
    SIPCreativeWorkSeason,
)
from app.mets import METS
from app.utils import ParseException


def to_sippy_lang_str(str: XMLLangStr | None) -> LangStr | None:
    if str is None:
        return None
    return LangStr.codes(**str.content)


def to_sippy_role(
    role: SIPRole, type: Literal["contributor", "creator", "publisher"]
) -> Role:

    if role.birth_date or role.death_date:
        member = Person(
            name=LangStr(nl=role.name),
            birth_date=EDTF_level1(value=role.birth_date) if role.birth_date else None,
            death_date=EDTF_level1(value=role.death_date) if role.death_date else None,
        )
    else:
        member = Thing(name=LangStr(nl=role.name))

    if role.role_name is None:
        match type:
            case "contributor":
                role_name = "Bijdrager"
            case "publisher":
                role_name = "Publisher"
            case "creator":
                role_name = "Maker"
    else:
        role_name = role.role_name

    return Role(
        role_name=role_name,
        creator=member if type == "creator" else None,
        publisher=member if type == "publisher" else None,
        contributor=member if type == "contributor" else None,
    )


def to_sippy_quantitive_value(
    measurement: Measurement | None,
) -> QuantitativeValue | None:

    if measurement is None:
        return None

    match measurement.unit_text:
        case "mm":
            unit_code = "MMT"
        case "cm":
            unit_code = "CMT"
        case "m":
            unit_code = "MTR"
        case "kg":
            unit_code = "KGM"

    return QuantitativeValue(
        value=Float(value=measurement.value),
        unit_text=measurement.unit_text,
        unit_code=unit_code,
    )


def to_sippy_creative_work(
    sip_creative_work: SIPAnyCreativeWork | SIPBroadcastEvent,
) -> AnyCreativeWork | BroadcastEvent:
    match sip_creative_work:
        case SIPBroadcastEvent():
            return BroadcastEvent()
        case SIPEpisode():
            # TODO hardcoded identifier
            return Episode(name=LangStr(nl=sip_creative_work.name), identifier="")
        case SIPArchiveComponent():
            return ArchiveComponent(name=LangStr(nl=sip_creative_work.name))
        case SIPCreativeWorkSeries():
            return CreativeWorkSeries(name=LangStr(nl=sip_creative_work.name))
        case SIPCreativeWorkSeason():
            return CreativeWorkSeason(name=LangStr(nl=sip_creative_work.name))


def parse_descriptive(mets: METS) -> dict[str, Any]:

    if mets.descriptive_metadata is None:
        raise ParseException("Package must have descriptive metdata")

    dc_schema = DCSchema.from_xml(str(mets.descriptive_metadata))
    return {
        "name": to_sippy_lang_str(dc_schema.title),
        "alternative_name": [to_sippy_lang_str(dc_schema.alternative)],
        # # TODO: dcterms:extend
        "available": (
            DateTime(value=dc_schema.available) if dc_schema.available else None
        ),
        "description": to_sippy_lang_str(dc_schema.description),
        "abstract": to_sippy_lang_str(dc_schema.abstract),
        "date_created": EDTF_level1(value=dc_schema.created),
        "date_published": (
            EDTF_level1(value=dc_schema.issued) if dc_schema.issued else None
        ),
        "publisher": [
            to_sippy_role(publisher, "publisher") for publisher in dc_schema.publisher
        ],
        "creator": [to_sippy_role(creator, "creator") for creator in dc_schema.creator],
        "contributor": [
            to_sippy_role(contributor, "contributor")
            for contributor in dc_schema.contributor
        ],
        "spatial": [Place(name=LangStr(nl=s)) for s in dc_schema.spatial],
        "temporal": [LangStr(nl=t) for t in dc_schema.temporal],
        "keywords": [to_sippy_lang_str(dc_schema.subject)] if dc_schema.subject else [],
        "in_language": dc_schema.language,
        # # TODO: is this simple mapping for licenses ok?
        "license": [
            Concept(id="https://data.hetarchief.be/id/license/" + l)
            for l in dc_schema.license
        ],
        "copyright_holder": (
            [Thing(name=LangStr(nl=dc_schema.rights_holder))]
            if dc_schema.rights_holder
            else []
        ),
        "rights": ([to_sippy_lang_str(dc_schema.rights)] if dc_schema.rights else []),
        "format": String(value=dc_schema.format),
        "height": to_sippy_quantitive_value(dc_schema.height),
        "width": to_sippy_quantitive_value(dc_schema.width),
        "depth": to_sippy_quantitive_value(dc_schema.depth),
        "weight": to_sippy_quantitive_value(dc_schema.weight),
        "art_medium": (
            [to_sippy_lang_str(dc_schema.art_medium)] if dc_schema.art_medium else []
        ),
        "artform": [to_sippy_lang_str(dc_schema.artform)] if dc_schema.artform else [],
        "schema_is_part_of": [
            to_sippy_creative_work(cw) for cw in dc_schema.is_part_of
        ],
        "credit_text": [LangStr(nl=s) for s in dc_schema.credit_text],
    }

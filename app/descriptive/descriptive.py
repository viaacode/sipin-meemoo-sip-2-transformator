from typing import Any

import sippy

from app.mets import METS
from app.descriptive.sippify import Sippify
from app.utils import ParseException
from app.descriptive.dc_schema import DCPlusSchema


def parse_descriptive(mets: METS) -> dict[str, Any]:

    if mets.descriptive_metadata is None:
        raise ParseException("Package must have descriptive metdata")

    desc = DCPlusSchema.from_xml(str(mets.descriptive_metadata))

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

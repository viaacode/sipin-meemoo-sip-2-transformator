from functools import partial

import sippy

from ..models import mets
from ..utils import ParseException

from .mods import parse_mods
from .dc_schema import parse_dc_schema


# TODO: make this generic so that id does not use the version of the SIP
def parse_descriptive(mets_info: mets.METS) -> partial[sippy.IntellectualEntity]:
    if mets_info.descriptive_metadata is None:
        raise ParseException(
            "SIP should have descriptive metadata at the package level"
        )

    match mets_info.other_content_information_type:
        case "https://data.hetarchief.be/id/sip/2.1/bibliographic":
            return parse_mods(mets_info.descriptive_metadata)
        case (
            "https://data.hetarchief.be/id/sip/2.1/basic"
            | "https://data.hetarchief.be/id/sip/2.1/material-artwork"
            | "https://data.hetarchief.be/id/sip/2.1/film"
        ):
            return parse_dc_schema(mets_info.descriptive_metadata)

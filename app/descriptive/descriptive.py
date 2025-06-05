from typing import Any

from app.mets import METS
from app.descriptive.mods import parse_mods
from app.descriptive.dc_schema import parse_dc_schema


# TODO: make this generic so that id does not use the version of the SIP
def parse_descriptive(mets: METS) -> dict[str, Any]:
    match mets.other_content_information_type:
        case "https://data.hetarchief.be/id/sip/2.1/bibliographic":
            return parse_mods(mets)
        case (
            "https://data.hetarchief.be/id/sip/2.1/basic"
            | "https://data.hetarchief.be/id/sip/2.1/material-artwork"
            | "https://data.hetarchief.be/id/sip/2.1/film"
        ):
            return parse_dc_schema(mets)

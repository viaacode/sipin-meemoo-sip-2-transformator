from functools import partial

import sippy

from ..structural.mets import OtherContentInformationType

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
        case OtherContentInformationType.BIBLIOGRAPHIC:
            return parse_mods(mets_info.descriptive_metadata)
        case (
            OtherContentInformationType.BASIC
            | OtherContentInformationType.MATERIAL_ARTWORK
            | OtherContentInformationType.FILM
        ):
            return parse_dc_schema(mets_info.descriptive_metadata)

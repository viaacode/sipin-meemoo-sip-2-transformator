from functools import partial

import sippy

from ..structural.mets import OtherContentInformationType

from ..models import mets
from ..utils import ParseException

from .mods import parse_mods
from .dc_schema import parse_dc_schema


def parse_descriptive(mets_info: mets.METS) -> partial[sippy.IntellectualEntity]:
    descriptive_metdata_path = mets_info.descriptive_metadata
    if descriptive_metdata_path is None:
        raise ParseException(
            "SIP should have descriptive metadata at the package level"
        )

    match mets_info.other_content_information_type:
        case OtherContentInformationType.BIBLIOGRAPHIC:
            return parse_mods(descriptive_metdata_path)
        case (
            OtherContentInformationType.BASIC
            | OtherContentInformationType.MATERIAL_ARTWORK
            | OtherContentInformationType.FILM
        ):
            return parse_dc_schema(descriptive_metdata_path)

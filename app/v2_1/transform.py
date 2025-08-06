from typing import Any
from pathlib import Path

from eark_models.utils import XMLParseable
import sippy.utils
import sippy

from .models import SIP, dcs
from .descriptive import parse_descriptive
from .preservation.premis import PreservationTransformer
from . import utils
from ..utils import get_sip_profile
from .mets.mets import parse_mets


sippy.utils.Config.SET_FIELDS_EXPLICIT = True


def transform_sip(unzipped_path: Path) -> dict[str, Any]:
    sip = transform_to_sippy(unzipped_path)
    return sip.serialize()


def transform_to_sippy(unzipped_path: Path) -> sippy.SIP:
    """
    Parse a meemoo SIP given its unzipped path.
    """

    profile = get_sip_profile(unzipped_path)
    DescriptiveModel = get_descriptive_model(profile)

    sip = SIP[DescriptiveModel].from_path(Path(unzipped_path), DescriptiveModel)

    premis_transformer = PreservationTransformer(sip)
    package_mets = parse_mets(sip.unzipped_path.joinpath("METS.xml"))
    ie_structural = premis_transformer.intellectual_entity_info
    ie_descriptive = parse_descriptive(package_mets)

    ie = sippy.IntellectualEntity(
        maintainer=package_mets.content_partner,
        **ie_structural.keywords,
        **ie_descriptive.keywords,
    )

    return sippy.SIP(
        mets_type=package_mets.type,
        profile=package_mets.other_content_information_type,
        entity=ie,
        events=premis_transformer.events,
        mets_agents=package_mets.agents,
        premis_agents=premis_transformer.premis_agents,
    )


def get_descriptive_model(profile: str) -> type[XMLParseable]:
    match profile:
        case "https://data.hetarchief.be/id/sip/2.1/basic":
            return dcs.DCPlusSchema
        case "https://data.hetarchief.be/id/sip/2.1/film":
            return dcs.DCPlusSchema
        case "https://data.hetarchief.be/id/sip/2.1/material-artwork":
            return dcs.DCPlusSchema
        case _:
            raise utils.TransformatorError(
                f"Received SIP with unsupported profile '{profile}'."
            )

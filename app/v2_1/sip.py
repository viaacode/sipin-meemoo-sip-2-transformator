from pathlib import Path

from sippy.sip import SIP, IntellectualEntity
from sippy.utils import Config

from .descriptive import parse_descriptive
from .preservation.premis import SIPStructuralInfo


Config.SET_FIELDS_EXPLICIT = False


def parse_sip(path: str | Path) -> SIP:
    """
    Parse a meemoo SIP given its root folder.
    """

    structural = SIPStructuralInfo(path)
    package_mets = structural.package.mets
    ie_structural = structural.intellectual_entity_info
    ie_descriptive = parse_descriptive(package_mets)

    ie = IntellectualEntity(
        type=package_mets.entity_type,
        maintainer=package_mets.content_partner,
        **ie_structural.keywords,
        **ie_descriptive.keywords,
    )

    return SIP(
        # TODO: fix hardcoded value
        profile="https://data.hetarchief.be/id/sip/2.1/basic",
        entity=ie,
        events=structural.events,
        mets_agents=package_mets.agents,
        premis_agents=structural.premis_agents,
    )

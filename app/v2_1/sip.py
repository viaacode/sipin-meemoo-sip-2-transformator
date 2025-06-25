from pathlib import Path

from sippy.sip import SIP, IntellectualEntity
from sippy.utils import Config

from .descriptive import parse_descriptive
from .mets import parse_mets
from .preservation.preservation import StructuralInfo


Config.SET_FIELDS_EXPLICIT = False


def parse_sip(path: str | Path) -> SIP:
    """
    Parse a meemoo SIP given its root folder.
    """

    mets_path = Path(path).joinpath("METS.xml")
    package_mets = parse_mets(mets_path)

    structural = StructuralInfo.from_mets(package_mets)
    ie_structural = structural.intellectual_entity
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

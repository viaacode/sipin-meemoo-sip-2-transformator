from pathlib import Path

from sippy.sip import SIP, IntellectualEntity
from sippy.utils import Config

from .descriptive import parse_descriptive
from .mets import parse_mets
from .preservation import PremisFiles


Config.SET_FIELDS_EXPLICIT = False


def parse_sip(path: str | Path) -> SIP:
    """
    Parse a meemoo SIP given its root folder.
    """

    mets_path = Path(path).joinpath("METS.xml")
    package_mets = parse_mets(mets_path)
    premis_files = PremisFiles(package_mets)
    ie_structural = premis_files.get_structural_info()
    ie_descriptive = parse_descriptive(package_mets)

    ie = IntellectualEntity(
        type=package_mets.entity_type,
        maintainer=package_mets.content_partner,
        **ie_structural.keywords,
        **ie_descriptive.keywords,
    )

    return SIP(
        entity=ie,
        events=premis_files.parse_events(),
        metsHdr=package_mets.metsHdr,
        premis_agents=premis_files.parse_premis_agents(),
    )

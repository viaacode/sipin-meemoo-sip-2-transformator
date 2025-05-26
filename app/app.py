from pathlib import Path

from sippy.sip import SIP, IntellectualEntity
from sippy.utils import Config, String
from sippy.vocabulary import EntityClass
from app.descriptive import parse_descriptive
from app.mets import parse_mets
from app.preservation import PremisFiles


Config.SET_FIELDS_EXPLICIT = False


def parse_sip(path) -> SIP:
    """
    Parse a meemoo SIP given its root folder.
    """

    mets_path = Path(path).joinpath("METS.xml")
    package_mets = parse_mets(mets_path)
    premis_files = PremisFiles(package_mets)
    structural = premis_files.get_structural_info()
    descriptive = parse_descriptive(package_mets)

    ie = IntellectualEntity(
        type=EntityClass.entity,  # TODO
        maintainer=package_mets.get_content_partner(),
        **structural,
        **descriptive,
    )

    events = premis_files.parse_events()

    return SIP(
        entity=ie,
        events=events,
        premis_agents=[],
    )

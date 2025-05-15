from pathlib import Path

from sippy.sip import IntellectualEntity
from sippy.utils import Config, String
from sippy.vocabulary import EntityClass
from app.descriptive import parse_descriptive
from app.mets import parse_mets
from app.preservation import PremisFiles


PATH = "/home/luca/Projects/documentation/assets/sip_samples/2.1/film_standard_mkv/uuid-2746e598-75cd-47b5-9a3e-8df18e98bb95"

Config.SET_FIELDS_EXPLICIT = False


def parse_package():

    mets_path = Path(PATH).joinpath("METS.xml")

    package_mets = parse_mets(mets_path)
    premis_files = PremisFiles(package_mets)

    structural = premis_files.get_structural_info()
    descriptive = parse_descriptive(package_mets)

    ie = IntellectualEntity(
        type=EntityClass.entity,  # TODO
        format=String(value="film"),  # TODO
        maintainer=package_mets.get_content_partner(),
        **structural,
        **descriptive,
    )

    print(ie)

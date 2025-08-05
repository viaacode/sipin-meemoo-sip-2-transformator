from pathlib import Path
import xml.etree.ElementTree as ET


class TransformatorError(Exception): ...


def get_sip_profile(unzipped_path: Path) -> str:
    root_mets_path = unzipped_path.joinpath("METS.xml")
    mets_root = ET.parse(root_mets_path).getroot()
    profile = mets_root.get(
        "{https://DILCIS.eu/XML/METS/CSIPExtensionMETS}OTHERCONTENTINFORMATIONTYPE"
    )
    if profile is None:
        raise TransformatorError("Could not determine profile.")
    return profile

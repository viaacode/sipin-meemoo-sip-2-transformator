from typing import Callable, Any
from pathlib import Path
import xml.etree.ElementTree as ET

from transformator import v2_1


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


def get_sip_transformator(profile: str) -> Callable[[Path], dict[str, Any]]:
    parts = profile.split("/")
    version = parts[-2]

    match version:
        case "2.1":
            return v2_1.transform_sip
        case _:
            raise TransformatorError("Invalid SIP profile found in received message.")

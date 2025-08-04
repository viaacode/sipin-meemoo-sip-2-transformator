from typing import Self, Any
from pathlib import Path

from pydantic.dataclasses import dataclass

import sippy.utils
import sippy

from .level import Level
from .descriptive import parse_descriptive
from .preservation.premis import PreservationTransformer


sippy.utils.Config.SET_FIELDS_EXPLICIT = True


@dataclass
class SIP:
    package: Level
    representations: list[Level]

    @classmethod
    def parse(cls, sip_path: Path) -> Self:
        package_level = Level.package(sip_path.joinpath("METS.xml"))
        representation_levels = [
            Level.representation(repr)
            for repr in package_level.mets_info.representations
        ]
        return cls(
            package=package_level,
            representations=representation_levels,
        )


def transform_sip(unzipped_path: str) -> dict[str, Any]:
    sip = transform_to_sippy(unzipped_path)
    return sip.serialize()


def transform_to_sippy(unzipped_path: str | Path) -> sippy.SIP:
    """
    Parse a meemoo SIP given its root folder.
    """

    sip = SIP.parse(Path(unzipped_path))
    preservation_parser = PreservationTransformer(sip.package, sip.representations)
    package_mets = preservation_parser.package.mets_info
    ie_structural = preservation_parser.intellectual_entity_info
    ie_descriptive = parse_descriptive(package_mets)

    ie = sippy.IntellectualEntity(
        maintainer=package_mets.content_partner,
        **ie_structural.keywords,
        **ie_descriptive.keywords,
    )

    return sippy.SIP(
        mets_type=sip.package.mets_info.type,
        profile=sip.package.mets_info.other_content_information_type,
        entity=ie,
        events=preservation_parser.events,
        mets_agents=package_mets.agents,
        premis_agents=preservation_parser.premis_agents,
    )

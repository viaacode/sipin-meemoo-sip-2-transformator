from typing import Self
from pathlib import Path

from pydantic.dataclasses import dataclass

import sippy.utils
import sippy

from .level import Level
from .descriptive import parse_descriptive
from .preservation.premis import PreservationParser


sippy.utils.Config.SET_FIELDS_EXPLICIT = False


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


def parse_sip(path: str | Path) -> sippy.SIP:
    """
    Parse a meemoo SIP given its root folder.
    """

    sip = SIP.parse(Path(path))
    preservation_parser = PreservationParser(sip.package, sip.representations)
    package_mets = preservation_parser.package.mets_info
    ie_structural = preservation_parser.intellectual_entity_info
    ie_descriptive = parse_descriptive(package_mets)

    ie = sippy.IntellectualEntity(
        type=package_mets.entity_type,
        maintainer=package_mets.content_partner,
        **ie_structural.keywords,
        **ie_descriptive.keywords,
    )

    return sippy.SIP(
        # TODO: fix hardcoded value
        profile="https://data.hetarchief.be/id/sip/2.1/basic",
        entity=ie,
        events=preservation_parser.events,
        mets_agents=package_mets.agents,
        premis_agents=preservation_parser.premis_agents,
    )

from pathlib import Path
import typing
from typing import cast
from enum import StrEnum

from lxml import etree
from lxml.etree import _Element
from pydantic import BaseModel

import sippy

from ..utils import (
    ParseException,
    xpath_element_list,
    xpath_text_list,
    xpath_optional_text,
    xpath_text,
)
from ..version import SIP_VERSION


OtherContentInformationType = StrEnum(
    "OtherContentInformationType",
    names={
        "BASIC": f"https://data.hetarchief.be/id/sip/{SIP_VERSION}/basic",
        "BIBLIOGRAPHIC": f"https://data.hetarchief.be/id/sip/{SIP_VERSION}/bibliographic",
        "MATERIAL_ARTWORK": f"https://data.hetarchief.be/id/sip/{SIP_VERSION}/material-artwork",
        "FILM": f"https://data.hetarchief.be/id/sip/{SIP_VERSION}/film",
    },
)


class METS(BaseModel):
    type: str
    other_content_information_type: OtherContentInformationType
    agents: list[sippy.METSAgent]
    descriptive_metadata: Path | None
    administrative_metadata: Path | None
    representations: list[Path]

    @property
    def content_partner(self) -> sippy.ContentPartner:
        """
        Gets the CP from the METS agents.
        """
        archivist = [
            agent
            for agent in self.agents
            if agent.role == "ARCHIVIST" and agent.type == "ORGANIZATION"
        ]
        if len(archivist) != 1:
            raise ParseException("No archivist agent found in METS")
        note = archivist[0].note
        if not isinstance(note, sippy.EARKNote):
            raise ParseException("Archivist note must be an e-ark note")

        archivist_name = archivist[0].name
        return sippy.ContentPartner(
            identifier=note.value,
            pref_label=sippy.UniqueLangStrings.codes(nl=archivist_name),
            name=sippy.UniqueLangStrings.codes(nl=archivist_name),
        )


def parse_mets(mets_path: Path) -> METS:
    root = mets_path.parent
    mets_xml = etree.parse(mets_path).getroot()

    agents_xml = xpath_element_list(mets_xml, "mets:metsHdr/mets:agent")
    agents = [parse_mets_agent(agent) for agent in agents_xml]

    struct_map_reprs = xpath_text_list(
        mets_xml,
        "mets:structMap[@LABEL='CSIP' and @TYPE='PHYSICAL']/mets:div/mets:div[starts-with(@LABEL, 'Representations')]/mets:mptr/@xlink:href",
    )
    struct_map_reprs = [root.joinpath(r) for r in struct_map_reprs]

    # TODO: perhaps the structmap should be used to get the ID of the dmdSec to read
    dmd_href = xpath_optional_text(
        mets_xml,
        "mets:dmdSec/mets:mdRef[@LOCTYPE='URL' and @xlink:type='simple']/@xlink:href",
    )
    amd_href = xpath_optional_text(
        mets_xml,
        "mets:amdSec/mets:digiprovMD/mets:mdRef[@LOCTYPE='URL' and @xlink:type='simple']/@xlink:href",
    )

    other_content_information_type = xpath_text(
        mets_xml, "@csip:OTHERCONTENTINFORMATIONTYPE"
    )

    allowed_contened_information_types = [o for o in OtherContentInformationType]
    if other_content_information_type not in allowed_contened_information_types:
        raise ValueError(
            f"OTHERCONTENTINFORMATIONTYPE must be one of {allowed_contened_information_types}"
        )
    other_content_information_type = OtherContentInformationType(
        other_content_information_type
    )
    type = xpath_text(mets_xml, "@TYPE")

    return METS(
        type=type,
        other_content_information_type=other_content_information_type,
        agents=agents,
        descriptive_metadata=(
            root.joinpath(dmd_href) if dmd_href is not None else dmd_href
        ),
        administrative_metadata=(
            root.joinpath(amd_href) if amd_href is not None else amd_href
        ),
        representations=struct_map_reprs,
    )


def parse_mets_agent(agent: _Element) -> sippy.METSAgent:
    role = xpath_text(agent, "@ROLE")
    type = xpath_optional_text(agent, "@TYPE")
    if role not in typing.get_args(sippy.METSRole):
        raise ParseException(f"@ROLE must be one of {typing.get_args(sippy.METSRole)}")
    if type not in typing.get_args(sippy.METSAgentType):
        raise ParseException(
            f"@TYPE must be one of {typing.get_args(sippy.METSAgentType)}"
        )

    return sippy.METSAgent(
        id=xpath_optional_text(agent, "@ID"),
        name=xpath_text(agent, "mets:name/text()"),
        note=sippy.EARKNote(
            note_type=xpath_text(agent, "mets:note/@csip:NOTETYPE"),
            value=xpath_text(agent, "mets:note/text()"),
        ),
        role=cast(sippy.METSRole, role),
        other_role=xpath_optional_text(agent, "@OTHERROLE"),
        type=cast(sippy.METSAgentType, type),
        other_type=xpath_optional_text(agent, "@OTHERTYPE"),
    )

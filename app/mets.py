from pathlib import Path
import typing
from typing import cast

from lxml import etree
from lxml.etree import _Element
from pydantic import BaseModel

from sippy.descriptive import ContentPartner
from sippy.sip import (
    EARKNote,
    METSAgent,
    METSAgentType,
    METSHdr,
    METSRole,
)
from sippy.utils import LangStr

from app.utils import (
    ParseException,
    xpath_element_list,
    xpath_text_list,
    xpath_optional_text,
    xpath_text,
)


class METS(BaseModel):
    metsHdr: METSHdr
    descriptive_metadata: Path | None
    administrative_metadata: Path | None
    representations: list[Path]

    def get_content_partner(self) -> ContentPartner:
        """
        Gets the CP from the METS agents.
        """
        archivist = [
            agent
            for agent in self.metsHdr.agents
            if agent.role == "ARCHIVIST" and agent.type == "ORGANIZATION"
        ]
        if len(archivist) != 1:
            raise ParseException("No archivist agent found in METS")
        note = archivist[0].note
        if not isinstance(note, EARKNote):
            raise ParseException("Archivist note must be an e-ark note")
        return ContentPartner(
            identifier=note.value,
            pref_label=LangStr.codes(nl=archivist[0].name),
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

    dmd_href = xpath_optional_text(
        mets_xml,
        "mets:dmdSec/mets:mdRef[@LOCTYPE='URL' and @xlink:type='simple']/@xlink:href",
    )
    amd_href = xpath_optional_text(
        mets_xml,
        "mets:amdSec/mets:digiprovMD/mets:mdRef[@LOCTYPE='URL' and @xlink:type='simple']/@xlink:href",
    )

    return METS(
        metsHdr=METSHdr(agents=agents),
        descriptive_metadata=(
            root.joinpath(dmd_href) if dmd_href is not None else dmd_href
        ),
        administrative_metadata=(
            root.joinpath(amd_href) if amd_href is not None else amd_href
        ),
        representations=struct_map_reprs,
    )


def parse_mets_agent(agent: _Element) -> METSAgent:
    role = xpath_text(agent, "@ROLE")
    type = xpath_optional_text(agent, "@TYPE")
    if role not in typing.get_args(METSRole):
        raise ParseException(f"@ROLE must be one of {typing.get_args(METSRole)}")
    if type not in typing.get_args(METSAgentType):
        raise ParseException(f"@TYPE must be one of {typing.get_args(METSAgentType)}")

    return METSAgent(
        id=xpath_optional_text(agent, "@ID"),
        name=xpath_text(agent, "mets:name/text()"),
        note=EARKNote(
            note_type=xpath_text(agent, "mets:note/@csip:NOTETYPE"),
            value=xpath_text(agent, "mets:note/text()"),
        ),
        role=cast(METSRole, role),
        other_role=xpath_optional_text(agent, "@OTHERROLE"),
        type=cast(METSAgentType, type),
        other_type=xpath_optional_text(agent, "@OTHERTYPE"),
    )

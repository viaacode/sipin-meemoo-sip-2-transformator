from typing import Self, TYPE_CHECKING

from pydantic import BaseModel

import eark_models.premis.v3_0 as premis


if TYPE_CHECKING:
    from .premis import SIPStructuralInfo


class TemporaryObject(BaseModel):
    id: premis.ObjectIdentifier

    @property
    def uuid(self) -> premis.ObjectIdentifier:
        if self.id.type.text != "UUID":
            raise AssertionError()
        return self.id


class Identifier(BaseModel, frozen=True):
    type: str
    value: str


class AgentMap(BaseModel):
    map: dict[Identifier, premis.Agent]

    @classmethod
    def create(cls, structural: "SIPStructuralInfo") -> Self:
        all_agents: list[premis.Agent] = []
        all_agents.extend(structural.package.premis.agents)
        for repr in structural.representations:
            all_agents.extend(repr.premis.agents)

        agent_map: dict[Identifier, premis.Agent] = {}
        for agent in all_agents:
            for id in agent.identifiers:
                id = Identifier(type=id.type.text, value=id.value.text)
                agent_map[id] = agent

        return cls(map=agent_map)

    def get(self, link: premis.LinkingAgentIdentifier) -> premis.Agent:
        id = Identifier(type=link.type.text, value=link.value.text)
        return self.map[id]


class ObjectMap(BaseModel):
    map: dict[Identifier, premis.Object]

    @classmethod
    def create(cls, structural: "SIPStructuralInfo") -> Self:
        all_objects: list[premis.Object] = []
        all_objects.extend(structural.package.premis.objects)
        for repr in structural.representations:
            all_objects.extend(repr.premis.objects)

        object_map: dict[Identifier, premis.Object] = {}
        for object in all_objects:
            for id in object.identifiers:
                id = Identifier(type=id.type.text, value=id.value.text)
                object_map[id] = object

        return cls(map=object_map)

    def _create_temporary_object(self, link) -> TemporaryObject:
        return TemporaryObject(
            id=premis.ObjectIdentifier(
                type=premis.ObjectIdentifierType(
                    text=link.type.text,
                    authority=link.type.authority,
                    authority_uri=link.type.authority_uri,
                    value_uri=link.type.value_uri,
                ),
                value=premis.ObjectIdentifierValue(text=link.value.text),
                simple_link=None,
            )
        )

    def get(
        self, link: premis.LinkingObjectIdentifier
    ) -> premis.Object | TemporaryObject:
        id = Identifier(type=link.type.text, value=link.value.text)
        if id not in self.map:
            return self._create_temporary_object(link)
        return self.map[id]

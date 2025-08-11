from typing import Self, TYPE_CHECKING

from pydantic import BaseModel

import eark_models.premis.v3_0 as premis


if TYPE_CHECKING:
    from .premis import PreservationTransformer


class TemporaryObject(BaseModel):
    """
    Events can produce temporary objects that are immediatly consumed by an other event.
    """

    id: premis.ObjectIdentifier

    @property
    def uuid(self) -> premis.ObjectIdentifier:
        if self.id.type.text != "UUID":
            raise AssertionError()
        return self.id


class Identifier(BaseModel, frozen=True):
    """
    Identifier for either an Agent or Object
    """

    type: str
    value: str


class AgentMap(BaseModel):
    """
    Map from a reference to an Agent to the actual Agent
    """

    map: dict[Identifier, premis.Agent]

    @classmethod
    def create(cls, transformer: "PreservationTransformer") -> Self:
        all_agents: list[premis.Agent] = []
        all_agents.extend(transformer.sip.metadata.preservation.agents)
        for repr in transformer.sip.representations:
            all_agents.extend(repr.metadata.preservation.agents)

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
    """
    Map from a reference to an Object to the actual Object or a TemporaryObject
    """

    map: dict[Identifier, premis.Object]

    @classmethod
    def create(cls, transformer: "PreservationTransformer") -> Self:
        all_objects: list[premis.Object] = []
        all_objects.extend(transformer.sip.metadata.preservation.objects)
        for repr in transformer.sip.representations:
            all_objects.extend(repr.metadata.preservation.objects)

        object_map: dict[Identifier, premis.Object] = {}
        for object in all_objects:
            for id in object.identifiers:
                id = Identifier(type=id.type.text, value=id.value.text)
                object_map[id] = object

        return cls(map=object_map)

    def _create_temporary_object(self, link) -> TemporaryObject:
        return TemporaryObject(
            id=premis.ObjectIdentifier(
                __source__="",
                type=premis.ObjectIdentifierType(
                    __source__="",
                    text=link.type.text,
                    authority=link.type.authority,
                    authority_uri=link.type.authority_uri,
                    value_uri=link.type.value_uri,
                ),
                value=premis.ObjectIdentifierValue(__source__="", text=link.value.text),
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

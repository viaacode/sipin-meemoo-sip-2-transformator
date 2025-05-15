from typing import Any, Self, Callable

from lxml import etree
from pydantic import BaseModel

from sippy.objects import (
    AnyRepresentation,
    CarrierRepresentation,
    DigitalRepresentation,
    File,
    LocalIdentifier,
    Reference,
)
from sippy.utils import NonNegativeInt
from sippy.vocabulary import Represents, haObj

from app.mets import METS, parse_mets
from app.utils import ParseException
from app.premis import (
    AgentIdentifier,
    Event as PremisEvent,
    LinkingAgent,
    LinkingAgentIdentifier,
    LinkingObject,
    LinkingObjectIdentifier,
    ObjectIdentifier,
    Premis,
    Agent as PremisAgent,
    Object as PremisObject,
    TemporaryObject,
)


class PremisFiles(BaseModel):
    package: Premis
    representations: list[Premis]

    @classmethod
    def from_package_mets(cls, package_mets: METS) -> Self:
        """
        Parse the package and representation PREMIS files.
        """
        if package_mets.administrative_metadata is None:
            raise ParseException("No package PREMIS found.")

        premis_xml = etree.parse(package_mets.administrative_metadata).getroot()
        package_premis = Premis.from_xml_tree(premis_xml)

        representations = []

        for path in package_mets.representations:
            repr_mets = parse_mets(path)
            if repr_mets.administrative_metadata is None:
                continue
            premis_xml = etree.parse(repr_mets.administrative_metadata).getroot()
            repr_premis = Premis.from_xml_tree(premis_xml)
            representations.append(repr_premis)

        return cls(
            package=package_premis,
            representations=representations,
        )

    def resolve_links(self):
        """
        TODO
        """
        # These also exist in premis but are not used in our SIP spec
        # linking_event_identifiers
        # linking_rights_statement_identifiers

        objects: list[PremisObject] = []
        objects.extend(self.package.objects)
        for repr in self.representations:
            objects.extend(repr.objects)

        agents: list[PremisAgent] = []
        agents.extend(self.package.agents)
        for repr in self.representations:
            agents.extend(repr.agents)

        events: list[PremisEvent] = []
        events.extend(self.package.events)
        for repr in self.representations:
            events.extend(repr.events)

        for event in events:
            linking_agents: list[LinkingAgent | LinkingAgentIdentifier] = []
            linking_objects: list[LinkingObject | LinkingObjectIdentifier] = []

            for linking_agent_id in event.linking_agents:
                # We can assume linking_agents to be of type `LinkingAgentIdentifier` here,
                # as that is the only value allowed by the PREMIS xsd
                if isinstance(linking_agent_id, LinkingAgent):
                    raise ParseException(
                        "Invalid premis file found while resolving links or `resolve_links` called twice."
                    )

                agent_id = AgentIdentifier(
                    type=linking_agent_id.type,
                    value=linking_agent_id.value,
                )
                includes_id = lambda agent, id: any(
                    id == _id for _id in agent.identifiers
                )
                agent = next(agent for agent in agents if includes_id(agent, agent_id))
                linking_agents.append(
                    LinkingAgent(
                        agent=agent,
                        roles=linking_agent_id.roles,
                    )
                )

            for linking_object_id in event.linking_objects:
                if isinstance(linking_object_id, LinkingObject):
                    raise ParseException(
                        "Invalid premis file found while resolving links or `resolve_links` called twice."
                    )

                object_id = ObjectIdentifier(
                    type=linking_object_id.type,
                    value=linking_object_id.value,
                )
                includes_id = lambda object, id: any(
                    id == _id for _id in object.identifiers
                )

                try:
                    object = next(
                        object for object in objects if includes_id(object, object_id)
                    )
                except StopIteration:
                    object = TemporaryObject(identifiers=[object_id])

                linking_objects.append(
                    LinkingObject(
                        object=object,
                        roles=linking_object_id.roles,
                    )
                )

            event.linking_agents = linking_agents
            event.linking_objects = linking_objects

    def get_structural_info(self) -> dict[str, Any]:
        """
        Extract the structural info from the package and representation PREMIS files.
        """
        structural = self.get_package_structural_info()
        digital_representations = self.get_digital_representations()

        is_represented_by = digital_representations
        if carrier := self.get_carrier_representation():
            is_represented_by += [carrier]

        structural |= {"is_represented_by": is_represented_by}
        return structural

    def get_package_structural_info(self) -> dict[str, Any]:
        """
        Extract the structural info available in the package PREMIS.
        """
        entity = self.package.entity
        entity_id = entity.pid.value if entity.pid else entity.uuid.value

        primary_identifiers = [
            LocalIdentifier(value=id.value)
            for id in entity.identifiers
            if id.is_primary_identifier
        ]
        local_identifiers = [
            LocalIdentifier(value=id.value)
            for id in entity.identifiers
            if id.is_local_identifier
        ]

        # Films have a carrier representation in the package PREMIS
        carrier = self.get_carrier_representation()

        # TODO: the SIP spec should be changed so that the carrier representation must
        # use the `has_carrier_copy` relationship, then the filtering of digital relationships
        # can be done easier
        digital_relationships = [
            rel
            for rel in entity.relationships
            if carrier and rel.related_object_uuid != carrier.id
        ]

        has_x_copy: Callable[[haObj], list[Reference]] = lambda x: [
            Reference(id=rel.related_object_uuid)
            for rel in digital_relationships
            if rel.sub_type.value_uri == x
        ]

        return {
            "identifier": entity_id,
            "primary_identifier": primary_identifiers,
            "local_identifier": local_identifiers,
            "has_carrier_copy": Reference(id=carrier.id) if carrier else None,
            "has_master_copy": has_x_copy(haObj.hasMasterCopy),
            "has_mezzanine_copy": has_x_copy(haObj.hasMasterCopy),
            "has_access_copy": has_x_copy(haObj.hasMasterCopy),
            "has_transcription_copy": has_x_copy(haObj.hasMasterCopy),
        }

    def get_carrier_representation(self) -> CarrierRepresentation | None:
        """
        Extract the carrier representation from the package PREMIS if present.
        """
        entity = self.package.entity
        entity_id = entity.pid.value if entity.pid else entity.uuid.value

        try:
            carrier = self.package.representation
        except StopIteration:
            carrier = None

        if carrier is not None:
            carrier = CarrierRepresentation(
                id=carrier.uuid.value,
                represents=Reference(id=entity_id),
                is_carrier_copy_of=Reference(id=entity_id),
                stored_at=[],  # TODO: the SIP spec must be finalized before this part can be parsed
            )

        return carrier

    def get_digital_representations(self) -> list[AnyRepresentation]:
        """
        Extract the digital representation from the representation PREMIS files.
        """
        digital_representations = []
        for repr_premis in self.representations:
            repr = repr_premis.representation

            files = []
            for file in repr_premis.files:
                size = next((c.size for c in file.characteristics if c.size))
                files.append(
                    File(
                        is_included_in=[Reference(id=repr.uuid.value)],
                        size=NonNegativeInt(value=size),
                    )
                )

            rep = next(
                (
                    rel
                    for rel in repr.relationships
                    if rel.sub_type.value_uri in Represents
                )
            )
            digital = DigitalRepresentation(
                id=repr.uuid.value,
                represents=Reference(id=rep.related_object_uuid),
                includes=files,
            )
            digital_representations.append(digital)

        return digital_representations

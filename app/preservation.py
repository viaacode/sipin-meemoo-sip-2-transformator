from typing import Any, Callable, cast

from lxml import etree
import dateutil.parser
from pydantic import BaseModel

from sippy.descriptive import Organization, Person
from sippy.events import (
    Agent,
    Event,
    EventAgentRole,
    EventClass,
    EventOutcome,
    EventRelObjRole,
    SoftwareAgent,
)
from sippy.objects import (
    AnyRepresentation,
    CarrierRepresentation,
    DigitalRepresentation,
    File,
    LocalIdentifier,
    Object,
    Reference,
)
from sippy.utils import DateTime, LangStr, NonNegativeInt, URIRef
from sippy.vocabulary import Represents, haObj

from app.mets import METS, parse_mets
from app.utils import ParseException
from app.premis import (
    AgentIdentifier,
    Event as PremisEvent,
    LinkingAgentIdentifier,
    LinkingObjectIdentifier,
    ObjectIdentifier,
    Premis,
    Agent as PremisAgent,
    Object as PremisObject,
    StringPlusAuthority,
)


class TemporaryObject(BaseModel):
    """
    Utility class used when resolving linking object identifiers.
    """

    identifiers: list[ObjectIdentifier]

    @property
    def uuid(self):
        return next((id for id in self.identifiers if id.is_uuid))


class AgentLink(BaseModel):
    """
    This is a utility class that does not exist in PREMIS.
    It is used for to replace `LinkingAgentIdentifiers` by the actual `Agent` that is referenced.
    """

    agent: PremisAgent
    roles: tuple[StringPlusAuthority, ...]

    @property
    def is_implementer(self) -> bool:
        return any([role.value_uri == EventAgentRole.imp for role in self.roles])

    @property
    def is_executer(self) -> bool:
        return any([role.value_uri == EventAgentRole.exe for role in self.roles])

    @property
    def has_no_role(self) -> bool:
        return len(self.roles) == 0


class ObjectLink(BaseModel):
    """
    This is a utility class that does not exist in PREMIS.
    It is used for to replace `LinkingObjectIdentifiers` by the actual `Object` that is referenced.
    """

    object: PremisObject | TemporaryObject
    roles: tuple[StringPlusAuthority, ...]

    @property
    def is_source(self):
        return any((role.value_uri == EventRelObjRole.sou for role in self.roles))

    @property
    def is_result(self):
        return any((role.value_uri == EventRelObjRole.out for role in self.roles))


class PremisFiles:
    package: Premis
    representations: list[Premis]
    agent_map: dict[LinkingAgentIdentifier, AgentLink]
    object_map: dict[LinkingObjectIdentifier, ObjectLink]

    def __init__(self, package_mets: METS):
        self.package = self.parse_package_file(package_mets)
        self.representations = self.parse_representation_files(package_mets)
        self.resolve_links()

    def parse_package_file(self, package_mets: METS):
        """
        Parse the package PREMIS file.
        """
        if package_mets.administrative_metadata is None:
            raise ParseException("No package PREMIS found.")

        premis_xml = etree.parse(package_mets.administrative_metadata).getroot()
        package_premis = Premis.from_xml_tree(premis_xml)
        return package_premis

    def parse_representation_files(self, package_mets: METS):
        """
        Parse the representation PREMIS files.
        """
        representations = []
        for path in package_mets.representations:
            repr_mets = parse_mets(path)
            if repr_mets.administrative_metadata is None:
                continue
            premis_xml = etree.parse(repr_mets.administrative_metadata).getroot()
            repr_premis = Premis.from_xml_tree(premis_xml)
            representations.append(repr_premis)
        return representations

    def resolve_links(self):
        """
        TODO
        """
        # These also exist in premis but are not used in our SIP spec
        # linking_event_identifiers
        # linking_rights_statement_identifiers

        all_objects: list[PremisObject] = []
        all_objects.extend(self.package.objects)
        for repr in self.representations:
            all_objects.extend(repr.objects)

        all_agents: list[PremisAgent] = []
        all_agents.extend(self.package.agents)
        for repr in self.representations:
            all_agents.extend(repr.agents)

        events: list[PremisEvent] = []
        events.extend(self.package.events)
        for repr in self.representations:
            events.extend(repr.events)

        self.agent_map = {}
        self.object_map = {}

        for event in events:
            for linking_agent_id in event.linking_agent_identifiers:
                # We can assume linking_agents to be of type `LinkingAgentIdentifier` here,
                # as that is the only value allowed by the PREMIS xsd
                if isinstance(linking_agent_id, AgentLink):
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
                agent = next(
                    agent for agent in all_agents if includes_id(agent, agent_id)
                )

                self.agent_map[linking_agent_id] = AgentLink(
                    agent=agent,
                    roles=linking_agent_id.roles,
                )

            for linking_object_id in event.linking_object_identifiers:
                if isinstance(linking_object_id, ObjectLink):
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
                        object
                        for object in all_objects
                        if includes_id(object, object_id)
                    )
                except StopIteration:
                    object = TemporaryObject(identifiers=[object_id])

                # Bug in Pydanintic-xml instanciates a list instead of tuple
                # when the the tuple/list is empty
                if type(linking_object_id.roles) is list:
                    linking_object_id = LinkingObjectIdentifier(
                        type=linking_object_id.type,
                        value=linking_object_id.value,
                        roles=(),
                        simple_link=linking_object_id.simple_link,
                    )

                self.object_map[linking_object_id] = ObjectLink(
                    object=object,
                    roles=linking_object_id.roles,
                )

    def get_agents_from_ids(
        self, agent_ids: list[LinkingAgentIdentifier]
    ) -> list[AgentLink]:
        return [self.agent_map[agent_id] for agent_id in agent_ids]

    def get_objects_from_ids(
        self, object_ids: list[LinkingObjectIdentifier]
    ) -> list[ObjectLink]:
        return [self.object_map[object_id] for object_id in object_ids]

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

    def parse_events(self) -> list[Event]:
        events = []
        premis_events = self.package.events
        for event in premis_events:
            type = cast(EventClass, event.type.value_uri)
            datetime = dateutil.parser.parse(event.datetime)

            agent_links = self.get_agents_from_ids(event.linking_agent_identifiers)

            impelementer_agent = next(
                (
                    agent_link.agent
                    for agent_link in agent_links
                    if agent_link.is_implementer
                )
            )
            executer_agent = next(
                (
                    agent_link.agent
                    for agent_link in agent_links
                    if agent_link.is_executer
                ),
                None,
            )
            executed_by = (
                SoftwareAgent(
                    id=executer_agent.primary_identifier.value,
                    name=LangStr(nl=executer_agent.name.innerText),
                    model=None,
                    serial_number=None,
                    version=None,
                )
                if executer_agent
                else None
            )

            associated_agents = [
                agent_link.agent for agent_link in agent_links if agent_link.has_no_role
            ]

            # TODO: could also be an organization
            # TODO: where to put agent type?
            was_associated_with: list[Agent] = [
                Person(
                    id=agent.uuid.value,
                    name=LangStr(nl=agent.name.innerText),
                    birth_date=None,
                    death_date=None,
                )
                for agent in associated_agents
            ]

            note = "\\n".join(
                [info.detail for info in event.detail_information if info.detail]
            )
            outcome_note = "\\n".join(
                [
                    "\\n".join(
                        [detail.note for detail in info.outcome_detail if detail.note]
                    )
                    for info in event.outcome_information
                ]
            )
            outcome = [
                info.outcome.value_uri
                for info in event.outcome_information
                if info.outcome and info.outcome.value_uri
            ]
            if len(outcome) > 1:
                raise ParseException("Only one outcome per event is supported.")
            outcome = outcome[0]

            object_links = self.get_objects_from_ids(event.linking_object_identifiers)
            source = [
                Reference(id=obj_link.object.uuid.value)
                for obj_link in object_links
                if obj_link.is_source
            ]
            result = [
                (
                    Reference(id=obj_link.object.uuid.value)
                    if isinstance(obj_link.object, TemporaryObject)
                    else Object(id=obj_link.object.uuid.value)
                )
                for obj_link in object_links
                if obj_link.is_result
            ]

            events.append(
                Event(
                    id=event.identifier.value.innerText,
                    type=type,
                    was_associated_with=was_associated_with,
                    started_at_time=DateTime(value=datetime),
                    ended_at_time=DateTime(value=datetime),
                    implemented_by=Organization(
                        identifier=impelementer_agent.primary_identifier.value,
                        pref_label=LangStr(nl=impelementer_agent.name.innerText),
                    ),
                    note=note if note else None,
                    outcome=URIRef(id=cast(EventOutcome, outcome)),
                    outcome_note=outcome_note if outcome_note else None,
                    executed_by=executed_by,
                    source=source,
                    result=result,
                    # TODO: instrument
                )
            )

        return events

from typing import Any, Callable, cast

from lxml import etree
import dateutil.parser
from pydantic import BaseModel

from sippy.descriptive import Organization, Person
from sippy.events import (
    Agent,
    Event,
    EventClass,
    EventOutcome,
    SoftwareAgent,
)
from sippy.objects import (
    AnyRepresentation,
    CarrierRepresentation,
    DigitalRepresentation,
    File,
    FileFormat,
    Fixity,
    LocalIdentifier,
    Object,
    Reference,
)
from sippy.utils import DateTime, LangStr, NonNegativeInt, URIRef
from sippy.vocabulary import Represents, RepresentsDigital

from app.mets import METS, parse_mets
from app.utils import ParseException
from eark_models.premis import (
    AgentIdentifier,
    Event as PremisEvent,
    LinkingAgentIdentifier,
    LinkingObjectIdentifier,
    ObjectIdentifier,
    Premis,
    Agent as PremisAgent,
    Object as PremisObject,
    StringPlusAuthority,
    Format as PremisFormat,
    File as PremisFile,
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
        return any([role.innerText == "implementer" for role in self.roles])

    @property
    def is_executer(self) -> bool:
        return any([role.innerText == "executer" for role in self.roles])

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
        return any((role.innerText == "source" for role in self.roles))

    @property
    def is_result(self):
        return any((role.innerText == "outcome" for role in self.roles))


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
        Creates a dict that maps agent/object identifiers to the agent/object themselves.
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

        digital_relationships = [
            rel
            for rel in entity.relationships
            if rel.sub_type.innerText in RepresentsDigital
        ]

        has_x_copy: Callable[[str], list[Reference]] = lambda x: [
            Reference(id=rel.related_object_uuid)
            for rel in digital_relationships
            if rel.sub_type.innerText == x
        ]

        return {
            "identifier": entity_id,
            "primary_identifier": primary_identifiers,
            "local_identifier": local_identifiers,
            "has_carrier_copy": Reference(id=carrier.id) if carrier else None,
            "has_master_copy": has_x_copy("has master copy"),
            "has_mezzanine_copy": has_x_copy("has mezzanine copy"),
            "has_access_copy": has_x_copy("has access copy"),
            "has_transcription_copy": has_x_copy("has transcription copy"),
        }

    def get_carrier_representation(self) -> CarrierRepresentation | None:
        """
        Extract the carrier representation from the package PREMIS if present.
        """
        rels = self.package.representation.relationships
        entity_rel = next(
            rel for rel in rels if rel.sub_type.innerText == "is carrier copy of"
        )
        entity_id = entity_rel.related_object_uuid

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
            files = [parse_file(file, repr.uuid.value) for file in repr_premis.files]
            relationship_to_entity = next(
                (
                    rel
                    for rel in repr.relationships
                    if rel.sub_type.innerText in Represents
                )
            )

            is_x_copy = lambda x: relationship_to_entity.sub_type.innerText == x
            is_master = is_x_copy(Represents.is_master_copy_of)
            is_mezzanine = is_x_copy(Represents.is_mezzanine_copy_of)
            is_access = is_x_copy(Represents.is_access_copy_of)
            is_transcription = is_x_copy(Represents.is_transcription_copy_of)
            reference = Reference(id=relationship_to_entity.related_object_uuid)

            digital = DigitalRepresentation(
                id=repr.uuid.value,
                represents=Reference(id=relationship_to_entity.related_object_uuid),
                includes=files,
                name=LangStr(nl="Digital Representation"),
                is_master_copy_of=reference if is_master else None,
                is_mezzanine_copy_of=reference if is_mezzanine else None,
                is_access_copy_of=reference if is_access else None,
                is_transcription_copy_of=reference if is_transcription else None,
            )
            digital_representations.append(digital)

        return digital_representations

    def parse_events(self) -> list[Event]:
        events = []
        premis_events = self.package.events
        for event in premis_events:
            type = cast(EventClass, map_event_type_to_uri(event.type.innerText))
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
                info.outcome.innerText
                for info in event.outcome_information
                if info.outcome
            ]
            if len(outcome) > 1:
                raise ParseException("Only one outcome per event is supported.")
            outcome = outcome[0]
            outcome = map_outcome_to_uri(outcome)

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
                    id=event.identifier.value,
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


def parse_file(file: PremisFile, repr_id: str) -> File:
    size = next((c.size for c in file.characteristics if c.size))
    fixity = next(iter(next((c.fixity for c in file.characteristics))))
    format = next(iter(next(c.format for c in file.characteristics)))

    return File(
        id=file.uuid.value,
        is_included_in=[Reference(id=repr_id)],
        size=NonNegativeInt(value=size),
        name=LangStr(nl="File"),
        original_name=(file.original_name.value if file.original_name else None),
        fixity=Fixity(
            type=map_fixity_digest_algorithm_to_uri(
                fixity.message_digest_algorithm.innerText
            ),
            value=fixity.message_digest,
        ),
        format=FileFormat(id=map_file_format_to_uri(format)),
    )


def map_outcome_to_uri(outcome: str) -> str:
    match outcome:
        case "success":
            return "http://id.loc.gov/vocabulary/preservation/eventOutcome/suc"
        case "fail":
            return "http://id.loc.gov/vocabulary/preservation/eventOutcome/fai"
        case "warning":
            return "http://id.loc.gov/vocabulary/preservation/eventOutcome/war"

    raise ParseException("Event outcome must be one of success, fail or warning.")


def map_event_type_to_uri(type: str) -> str:
    return "https://data.hetarchief.be/id/event-type/" + type


def map_fixity_digest_algorithm_to_uri(algorithm: str) -> str:
    if algorithm == "md5" or algorithm == "MD5":
        return (
            "http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions/md5"
        )

    raise ParseException(f"Unknown fixity message digest algorithm {algorithm}")


def map_file_format_to_uri(format: PremisFormat) -> str:
    if not format.registry:
        raise ParseException("Format registry must be present")
    if format.registry.name.innerText != "PRONOM":
        raise ParseException("Only the PRONOM format registry is supported")

    format_key = format.registry.key.innerText
    return "https://www.nationalarchives.gov.uk/pronom/" + format_key

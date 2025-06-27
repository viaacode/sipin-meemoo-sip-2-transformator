from typing import Self, cast
from functools import partial
from pathlib import Path

from pydantic.dataclasses import dataclass

import sippy
from ..models import premis

from .premis_utils import AgentMap, ObjectMap, TemporaryObject

from ..mets import METS, parse_mets
from ..utils import ParseException


@dataclass
class StructuralInfo:
    """Structural metadata of either the package level or the representation level."""

    relative_path: Path
    mets: METS
    premis_info: premis.Premis

    @classmethod
    def from_path(cls, path: Path, sip_path: Path) -> Self:
        mets_path = path.joinpath("METS.xml")
        mets = parse_mets(mets_path)

        return cls(
            mets=mets,
            premis_info=StructuralInfo.parse_premis(mets),
            relative_path=path.relative_to(sip_path),
        )

    @staticmethod
    def parse_premis(mets: METS) -> premis.Premis:
        if mets.administrative_metadata is None:
            raise ParseException("No PREMIS found.")
        return premis.Premis.from_xml(mets.administrative_metadata)


class SIPStructuralInfo:
    """Structural metadata of the entire SIP."""

    def __init__(self, sip_path: str | Path) -> None:
        root_path = Path(sip_path)
        parent_path = root_path.parent
        self.package = StructuralInfo.from_path(root_path, parent_path)
        self.representations = [
            StructuralInfo.from_path(p.parent, parent_path)
            for p in self.package.mets.representations
        ]

    @property
    def intellectual_entity_info(self) -> partial[sippy.IntellectualEntity]:
        """
        Extract the structural info from the package and representation PREMIS files.
        """
        structural = self.get_package_level_structural_info()
        digital_representations = self.get_digital_representations()

        is_represented_by = digital_representations
        if carrier := self.get_carrier_representation():
            is_represented_by += [carrier]

        return partial(structural, is_represented_by=is_represented_by)

    def get_package_level_structural_info(self) -> partial[sippy.IntellectualEntity]:
        entity = self.package.premis_info.entity
        entity_id = entity.pid.value.text if entity.pid else entity.uuid.value.text

        primary_identifiers = [
            sippy.LocalIdentifier(value=id.value.text)
            for id in entity.identifiers
            if id.is_primary_identifier
        ]
        local_identifiers = [
            sippy.LocalIdentifier(value=id.value.text)
            for id in entity.identifiers
            if id.is_local_identifier
        ]

        # Films have a carrier representation in the package PREMIS
        carrier = self.get_carrier_representation()

        return partial(
            sippy.IntellectualEntity,
            id=entity.uuid.value.text,
            identifier=entity_id,
            primary_identifier=primary_identifiers,
            local_identifier=local_identifiers,
            has_carrier_copy=sippy.Reference(id=carrier.id) if carrier else None,
            has_master_copy=filter_digital_relationships_by_name(
                entity.relationships, "has master copy"
            ),
            has_mezzanine_copy=filter_digital_relationships_by_name(
                entity.relationships, "has mezzanine copy"
            ),
            has_access_copy=filter_digital_relationships_by_name(
                entity.relationships, "has access copy"
            ),
            has_transcription_copy=filter_digital_relationships_by_name(
                entity.relationships, "has transcription copy"
            ),
        )

    def get_carrier_representation(self) -> sippy.CarrierRepresentation | None:
        """
        Extract the carrier representation from the package PREMIS if present.
        """

        try:
            carrier = self.package.premis_info.representation
        except StopIteration:
            # No carrier was found
            return None

        return CarrierRepresentationParser(self.package).parse_carrier_representation()

    def get_digital_representations(self) -> list[sippy.DigitalRepresentation]:
        """
        Extract the digital representation from the representation PREMIS files.
        """
        return [
            RepresentationLevelParser(repr).parse_digital_representation()
            for repr in self.representations
        ]

    @property
    def events(self) -> list[sippy.Event]:
        sippify = EventParser(self)
        return [sippify.parse(event) for event in self.package.premis_info.events]

    @property
    def premis_agents(self) -> list[sippy.PremisAgent]:
        return [
            sippy.PremisAgent(
                identifier=agent.uuid.value.text,
                name=agent.name.text,
                type=agent.type.text,
            )
            for agent in self.package.premis_info.agents
            if any(id.is_uuid for id in agent.identifiers)
        ]


def map_fixity_digest_algorithm_to_uri(algorithm: str) -> str:
    if algorithm == "md5" or algorithm == "MD5":
        return (
            "http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions/md5"
        )

    raise ParseException(f"Unknown fixity message digest algorithm {algorithm}")


def map_file_format_to_uri(format: premis.Format) -> str:
    if not format.registry:
        raise ParseException("Format registry must be present")
    if format.registry.name.text != "PRONOM":
        raise ParseException("Only the PRONOM format registry is supported")

    format_key = format.registry.key.text
    return "https://www.nationalarchives.gov.uk/pronom/" + format_key


def is_digital_relationship(rel: premis.Relationship) -> bool:
    return (
        rel.sub_type.text in sippy.IsRepresentedBy
        and rel.sub_type.text != sippy.IsRepresentedBy.has_carrier_copy
    )


def filter_digital_relationships_by_name(
    relationships: list[premis.Relationship], name: str
) -> list[sippy.Reference]:
    return [
        sippy.Reference(id=rel.related_object_uuid)
        for rel in relationships
        if is_digital_relationship(rel) and rel.sub_type.text == name
    ]


@dataclass
class RepresentationLevelParser:
    sip_representation: StructuralInfo

    def is_digital_relationship(self, relationship: premis.Relationship) -> bool:
        return relationship.sub_type.text in sippy.Represents

    def parse_digital_representation(self) -> sippy.DigitalRepresentation:
        premis_repr = self.sip_representation.premis_info.representation
        files = [
            self.parse_file(file) for file in self.sip_representation.premis_info.files
        ]
        relationship_to_entity = next(
            (
                rel
                for rel in premis_repr.relationships
                if self.is_digital_relationship(rel)
            )
        )

        reference = sippy.Reference(id=relationship_to_entity.related_object_uuid)

        is_master_copy_of = None
        is_mezzanine_copy_of = None
        is_access_copy_of = None
        is_transcription_copy_of = None

        match relationship_to_entity.sub_type.text:
            case sippy.Represents.is_master_copy_of:
                is_master_copy_of = reference
            case sippy.Represents.is_mezzanine_copy_of:
                is_mezzanine_copy_of = reference
            case sippy.Represents.is_access_copy_of:
                is_access_copy_of = reference
            case sippy.Represents.is_transcription_copy_of:
                is_transcription_copy_of = reference

        return sippy.DigitalRepresentation(
            id=premis_repr.uuid.value.text,
            represents=reference,
            includes=files,
            name=sippy.LangStr(nl="Digital Representation"),
            is_master_copy_of=is_master_copy_of,
            is_mezzanine_copy_of=is_mezzanine_copy_of,
            is_access_copy_of=is_access_copy_of,
            is_transcription_copy_of=is_transcription_copy_of,
        )

    def parse_file(self, file: premis.File) -> sippy.File:
        size = next((c.size for c in file.characteristics if c.size is not None))
        fixity = next(iter(next(c.fixity for c in file.characteristics)))
        format = next(iter(next(c.format for c in file.characteristics)))

        if file.original_name is None:
            raise ParseException()

        original_name = file.original_name.text
        relative_path = self.sip_representation.relative_path

        premis_representation = self.sip_representation.premis_info.representation
        representation_identifier = premis_representation.uuid.value.text

        return sippy.File(
            id=file.uuid.value.text,
            is_included_in=[sippy.Reference(id=representation_identifier)],
            size=sippy.NonNegativeInt(value=size.value),
            name=sippy.LangStr(nl="File"),
            original_name=original_name,
            fixity=sippy.Fixity(
                # TODO: creator
                id=sippy.uuid4(),
                type=map_fixity_digest_algorithm_to_uri(
                    fixity.message_digest_algorithm.text
                ),
                value=fixity.message_digest.text,
            ),
            format=sippy.FileFormat(id=map_file_format_to_uri(format)),
            stored_at=sippy.StorageLocation(
                file_path=str(relative_path.joinpath("data").joinpath(original_name))
            ),
        )


@dataclass
class CarrierRepresentationParser:
    sip_package: StructuralInfo

    def is_carrier_relationship(self, relationship: premis.Relationship) -> bool:
        return relationship.sub_type.text == "is carrier copy of"

    def parse_carrier_representation(self) -> sippy.CarrierRepresentation:
        carrier = self.sip_package.premis_info.representation

        relationship_to_entity = next(
            rel for rel in carrier.relationships if self.is_carrier_relationship(rel)
        )
        entity_id = sippy.Reference(id=relationship_to_entity.related_object_uuid)

        return sippy.CarrierRepresentation(
            id=carrier.uuid.value.text,
            represents=entity_id,
            is_carrier_copy_of=entity_id,
            stored_at=[],  # TODO: the SIP spec must be finalized before this part can be parsed
        )


class EventParser:
    def __init__(self, structural: "SIPStructuralInfo") -> None:
        self.agent_map = AgentMap.create(structural)
        self.object_map = ObjectMap.create(structural)

    def parse(self, event: premis.Event) -> sippy.Event:
        type = cast(sippy.EventClass, self.map_event_type_to_uri(event.type.text))

        return sippy.Event(
            id=event.identifier.value.text,
            type=type,
            was_associated_with=self.was_associated_with(event),
            started_at_time=sippy.DateTime(value=event.datetime.text),
            ended_at_time=sippy.DateTime(value=event.datetime.text),
            implemented_by=self.implemented_by(event),
            note=self.note(event),
            outcome=self.outcome(event),
            outcome_note=self.outcome_note(event),
            executed_by=self.executed_by(event),
            source=self.source(event),
            result=self.result(event),
            instrument=self.instrument(event),
        )

    def object_is_result(self, link: premis.LinkingObjectIdentifier) -> bool:
        return any((role.text == "outcome" for role in link.roles))

    def result(self, event: premis.Event) -> list[sippy.Reference | sippy.Object]:
        # Objects produced by the event
        result = [
            link
            for link in event.linking_object_identifiers
            if self.object_is_result(link)
        ]

        # Map the objects from their "link" to the actual object
        result = [self.object_map.get(link) for link in result]

        # References to the "result" objects
        object_references = [
            sippy.Reference(id=obj.uuid.value.text)
            for obj in result
            if isinstance(obj, premis.Object)
        ]

        # Temporary objects are objects that are produced by one event and immeadiatly consumed by another event.
        # They are not persisted as a premis:object because they are not relevant.
        temporary_objects = [
            sippy.Object(id=obj.uuid.value.text)
            for obj in result
            if isinstance(obj, TemporaryObject)
        ]

        return object_references + temporary_objects

    def object_is_source(self, link: premis.LinkingObjectIdentifier) -> bool:
        return any((role.text == "source" for role in link.roles))

    def source(self, event: premis.Event) -> list[sippy.Reference]:
        source_objects = [
            self.object_map.get(link)
            for link in event.linking_object_identifiers
            if self.object_is_source(link)
        ]
        return [sippy.Reference(id=obj.uuid.value.text) for obj in source_objects]

    def note(self, event: premis.Event) -> str | None:
        details = [info.detail.text for info in event.detail_information if info.detail]
        if len(details) == 0:
            return None
        return "\\n".join(details)

    def outcome(self, event: premis.Event) -> sippy.URIRef[sippy.EventOutcome] | None:
        outcomes = [
            info.outcome.text for info in event.outcome_information if info.outcome
        ]
        if len(outcomes) == 0:
            return None
        outcome = self.map_outcome_to_uri(outcomes[0])
        return sippy.URIRef[sippy.EventOutcome](id=outcome)

    def map_outcome_to_uri(self, outcome: str) -> sippy.EventOutcome:
        match outcome:
            case "success":
                return "http://id.loc.gov/vocabulary/preservation/eventOutcome/suc"
            case "fail":
                return "http://id.loc.gov/vocabulary/preservation/eventOutcome/fai"
            case "warning":
                return "http://id.loc.gov/vocabulary/preservation/eventOutcome/war"

        raise ParseException("Event outcome must be one of success, fail or warning.")

    def outcome_note(self, event: premis.Event) -> str | None:
        outcome_note = "\\n".join(
            [
                "\\n".join(
                    [detail.note.text for detail in info.outcome_detail if detail.note]
                )
                for info in event.outcome_information
            ]
        )
        if outcome_note == "":
            return None
        return outcome_note

    def agent_is_implementer(self, link: premis.LinkingAgentIdentifier) -> bool:
        return any([role.text == "implementer" for role in link.roles])

    def implemented_by(self, event: premis.Event) -> sippy.AnyOrganization:
        agents = (
            self.agent_map.get(link)
            for link in event.linking_agent_identifiers
            if self.agent_is_implementer(link)
        )
        implementer_agent = next(agents)
        return sippy.Organization(
            identifier=implementer_agent.primary_identifier.value.text,
            pref_label=sippy.LangStr(nl=implementer_agent.name.text),
        )

    def agent_is_executer(self, link: premis.LinkingAgentIdentifier) -> bool:
        return any([role.text == "executer" for role in link.roles])

    def executed_by(self, event: premis.Event) -> sippy.SoftwareAgent | None:
        agents = (
            self.agent_map.get(link)
            for link in event.linking_agent_identifiers
            if self.agent_is_executer(link)
        )
        executer_agent = next(agents, None)
        if executer_agent is None:
            return None

        return sippy.SoftwareAgent(
            id=executer_agent.primary_identifier.value.text,
            name=sippy.LangStr(nl=executer_agent.name.text),
            model=None,
            serial_number=None,
            version=None,
        )

    def agent_is_instrument(self, link: premis.LinkingAgentIdentifier) -> bool:
        return any([role.text == "instrument" for role in link.roles])

    def instrument(self, event: premis.Event) -> list[sippy.HardwareAgent]:
        instrument_agents = [
            self.agent_map.get(link)
            for link in event.linking_agent_identifiers
            if self.agent_is_instrument(link)
        ]
        return [
            sippy.HardwareAgent(
                name=sippy.LangStr(nl=ag.name.text),
                model=None,
                serial_number=None,
                version=None,
            )
            for ag in instrument_agents
        ]

    def agent_has_no_roles(self, link: premis.LinkingAgentIdentifier) -> bool:
        return len(link.roles) == 0

    def was_associated_with(self, event: premis.Event) -> list[sippy.Agent]:
        associated_agents = [
            self.agent_map.get(link)
            for link in event.linking_agent_identifiers
            if self.agent_has_no_roles(link)
        ]

        # TODO: could also be an organization
        return [
            sippy.Person(
                id=agent.uuid.value.text,
                name=sippy.LangStr(nl=agent.name.text),
                birth_date=None,
                death_date=None,
            )
            for agent in associated_agents
        ]

    def map_event_type_to_uri(self, type: str) -> str:
        return "https://data.hetarchief.be/id/event-type/" + type

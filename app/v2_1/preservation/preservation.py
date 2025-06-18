from typing import cast, Self, Callable
from functools import partial

from lxml import etree
import dateutil.parser
from pydantic import BaseModel

import sippy
import eark_models.premis.v3_0 as premis

from ..mets import METS, parse_mets
from ..utils import ParseException


class TemporaryObject(BaseModel):
    id: premis.ObjectIdentifier

    @property
    def uuid(self) -> premis.ObjectIdentifier:
        if self.id.type.innerText != "UUID":
            raise AssertionError()
        return self.id


class Identifier(BaseModel, frozen=True):
    type: str
    value: str


class AgentMap(BaseModel):
    map: dict[Identifier, premis.Agent]

    @classmethod
    def create(cls, structural: "StructuralInfo") -> Self:
        all_agents: list[premis.Agent] = []
        all_agents.extend(structural.package.agents)
        for repr in structural.representations:
            all_agents.extend(repr.agents)

        agent_map: dict[Identifier, premis.Agent] = {}
        for agent in all_agents:
            for id in agent.identifiers:
                id = Identifier(type=id.type.innerText, value=id.value)
                agent_map[id] = agent

        return cls(map=agent_map)

    def get(self, link: premis.LinkingAgentIdentifier) -> premis.Agent:
        id = Identifier(type=link.type.innerText, value=link.value)
        return self.map[id]


class ObjectMap(BaseModel):
    map: dict[Identifier, premis.Object]

    @classmethod
    def create(cls, structural: "StructuralInfo") -> Self:
        all_objects: list[premis.Object] = []
        all_objects.extend(structural.package.objects)
        for repr in structural.representations:
            all_objects.extend(repr.objects)

        object_map: dict[Identifier, premis.Object] = {}
        for object in all_objects:
            for id in object.identifiers:
                id = Identifier(type=id.type.innerText, value=id.value)
                object_map[id] = object

        return cls(map=object_map)

    def get(
        self, link: premis.LinkingObjectIdentifier
    ) -> premis.Object | TemporaryObject:
        id = Identifier(type=link.type.innerText, value=link.value)
        if id not in self.map:
            return TemporaryObject(
                id=premis.ObjectIdentifier(type=link.type, value=link.value)
            )
        return self.map[id]


class StructuralInfo(BaseModel):
    package: premis.Premis
    representations: list[premis.Premis]

    @classmethod
    def from_mets(cls, package_mets: METS) -> Self:
        package = StructuralInfo.parse_package_premis(package_mets)
        representations = StructuralInfo.parse_representation_premis(package_mets)
        return cls(
            package=package,
            representations=representations,
        )

    @staticmethod
    def parse_package_premis(package_mets: METS) -> premis.Premis:
        if package_mets.administrative_metadata is None:
            raise ParseException("No package PREMIS found.")

        premis_xml = etree.parse(package_mets.administrative_metadata).getroot()
        package_premis = premis.Premis.from_xml_tree(premis_xml)
        return package_premis

    @staticmethod
    def parse_representation_premis(package_mets: METS) -> list[premis.Premis]:
        representations: list[premis.Premis] = []
        for path in package_mets.representations:
            repr_mets = parse_mets(path)
            if repr_mets.administrative_metadata is None:
                continue
            premis_xml = etree.parse(repr_mets.administrative_metadata).getroot()
            repr_premis = premis.Premis.from_xml_tree(premis_xml)
            representations.append(repr_premis)
        return representations

    @property
    def intellectual_entity(self) -> partial[sippy.IntellectualEntity]:
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
        entity = self.package.entity
        entity_id = entity.pid.value if entity.pid else entity.uuid.value

        primary_identifiers = [
            sippy.LocalIdentifier(value=id.value)
            for id in entity.identifiers
            if id.is_primary_identifier
        ]
        local_identifiers = [
            sippy.LocalIdentifier(value=id.value)
            for id in entity.identifiers
            if id.is_local_identifier
        ]

        # Films have a carrier representation in the package PREMIS
        carrier = self.get_carrier_representation()

        return partial(
            sippy.IntellectualEntity,
            id=entity.uuid.value,
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
            carrier = self.package.representation
        except StopIteration:
            # No carrier was found
            return None

        entity_rel = next(
            rel
            for rel in carrier.relationships
            if rel.sub_type.innerText == "is carrier copy of"
        )
        entity_id = entity_rel.related_object_uuid

        return sippy.CarrierRepresentation(
            id=carrier.uuid.value,
            represents=sippy.Reference(id=entity_id),
            is_carrier_copy_of=sippy.Reference(id=entity_id),
            stored_at=[],  # TODO: the SIP spec must be finalized before this part can be parsed
        )

    def get_digital_representations(self) -> list[sippy.AnyRepresentation]:
        # TODO: fix return type hint
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
                    if rel.sub_type.innerText in sippy.Represents
                )
            )

            is_x_copy = lambda x: relationship_to_entity.sub_type.innerText == x
            is_master = is_x_copy(sippy.Represents.is_master_copy_of)
            is_mezzanine = is_x_copy(sippy.Represents.is_mezzanine_copy_of)
            is_access = is_x_copy(sippy.Represents.is_access_copy_of)
            is_transcription = is_x_copy(sippy.Represents.is_transcription_copy_of)
            reference = sippy.Reference(id=relationship_to_entity.related_object_uuid)

            digital = sippy.DigitalRepresentation(
                id=repr.uuid.value,
                represents=sippy.Reference(
                    id=relationship_to_entity.related_object_uuid
                ),
                includes=files,
                name=sippy.LangStr(nl="Digital Representation"),
                is_master_copy_of=reference if is_master else None,
                is_mezzanine_copy_of=reference if is_mezzanine else None,
                is_access_copy_of=reference if is_access else None,
                is_transcription_copy_of=reference if is_transcription else None,
            )
            digital_representations.append(digital)

        return digital_representations

    @property
    def events(self) -> list[sippy.Event]:
        agent_map = AgentMap.create(self)
        object_map = ObjectMap.create(self)
        return [
            Event2Sippy.parse(
                event=event,
                agent_map=agent_map,
                object_map=object_map,
            )
            for event in self.package.events
        ]

    @property
    def premis_agents(self) -> list[sippy.PremisAgent]:
        return [
            sippy.PremisAgent(
                identifier=agent.uuid.value,
                name=agent.name.innerText,
                type=agent.type.innerText,
            )
            for agent in self.package.agents
            if any(id.is_uuid for id in agent.identifiers)
        ]


def parse_file(file: premis.File, repr_id: str) -> sippy.File:
    size = next((c.size for c in file.characteristics if c.size is not None))
    fixity = next(iter(next(c.fixity for c in file.characteristics)))
    format = next(iter(next(c.format for c in file.characteristics)))

    return sippy.File(
        id=file.uuid.value,
        is_included_in=[sippy.Reference(id=repr_id)],
        size=sippy.NonNegativeInt(value=size),
        name=sippy.LangStr(nl="File"),
        original_name=(file.original_name.value if file.original_name else None),
        fixity=sippy.Fixity(
            # TODO: creator
            id=sippy.uuid4(),
            type=map_fixity_digest_algorithm_to_uri(
                fixity.message_digest_algorithm.innerText
            ),
            value=fixity.message_digest,
        ),
        format=sippy.FileFormat(id=map_file_format_to_uri(format)),
    )


def map_event_type_to_uri(type: str) -> str:
    return "https://data.hetarchief.be/id/event-type/" + type


def map_fixity_digest_algorithm_to_uri(algorithm: str) -> str:
    if algorithm == "md5" or algorithm == "MD5":
        return (
            "http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions/md5"
        )

    raise ParseException(f"Unknown fixity message digest algorithm {algorithm}")


def map_file_format_to_uri(format: premis.Format) -> str:
    if not format.registry:
        raise ParseException("Format registry must be present")
    if format.registry.name.innerText != "PRONOM":
        raise ParseException("Only the PRONOM format registry is supported")

    format_key = format.registry.key.innerText
    return "https://www.nationalarchives.gov.uk/pronom/" + format_key


def is_digital_relationship(rel: premis.Relationship) -> bool:
    return (
        rel.sub_type.innerText in sippy.IsRepresentedBy
        and rel.sub_type.innerText != sippy.IsRepresentedBy.has_carrier_copy
    )


def filter_digital_relationships_by_name(
    relationships: list[premis.Relationship], name: str
) -> list[sippy.Reference]:
    return [
        sippy.Reference(id=rel.related_object_uuid)
        for rel in relationships
        if is_digital_relationship(rel) and rel.sub_type.innerText == name
    ]


class Event2Sippy(BaseModel):
    event: premis.Event
    agent_map: AgentMap
    object_map: ObjectMap

    @staticmethod
    def parse(event: premis.Event, agent_map: AgentMap, object_map: ObjectMap):

        sippify = Event2Sippy(
            event=event,
            agent_map=agent_map,
            object_map=object_map,
        )

        type = cast(sippy.EventClass, map_event_type_to_uri(event.type.innerText))
        datetime = dateutil.parser.parse(event.datetime)

        return sippy.Event(
            id=event.identifier.value,
            type=type,
            was_associated_with=sippify.was_associated_with,
            started_at_time=sippy.DateTime(value=datetime),
            ended_at_time=sippy.DateTime(value=datetime),
            implemented_by=sippify.implemented_by,
            note=sippify.note,
            outcome=sippify.outcome,
            outcome_note=sippify.outcome_note,
            executed_by=sippify.executed_by,
            source=sippify.source,
            result=sippify.result,
            instrument=sippify.instrument,
        )

    @property
    def result(self) -> list[sippy.Reference | sippy.Object]:
        is_result: Callable[[premis.LinkingObjectIdentifier], bool] = lambda link: any(
            (role.innerText == "outcome" for role in link.roles)
        )
        result = [
            self.object_map.get(link)
            for link in self.event.linking_object_identifiers
            if is_result(link)
        ]

        refs = [
            sippy.Reference(id=obj.uuid.value)
            for obj in result
            if isinstance(obj, premis.Object)
        ]

        objects = [
            sippy.Object(id=obj.uuid.value)
            for obj in result
            if isinstance(obj, TemporaryObject)
        ]

        return refs + objects

    @property
    def source(self) -> list[sippy.Reference]:
        is_source: Callable[[premis.LinkingObjectIdentifier], bool] = lambda link: any(
            (role.innerText == "source" for role in link.roles)
        )
        source_objects = [
            self.object_map.get(link)
            for link in self.event.linking_object_identifiers
            if is_source(link)
        ]
        return [sippy.Reference(id=obj.uuid.value) for obj in source_objects]

    @property
    def note(self) -> str | None:
        details = [info.detail for info in self.event.detail_information if info.detail]
        if len(details) == 0:
            return None
        return "\\n".join(details)

    @property
    def outcome(self) -> sippy.URIRef[sippy.EventOutcome] | None:
        outcomes = [
            info.outcome.innerText
            for info in self.event.outcome_information
            if info.outcome
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

    @property
    def outcome_note(self) -> str | None:
        outcome_note = "\\n".join(
            [
                "\\n".join(
                    [detail.note for detail in info.outcome_detail if detail.note]
                )
                for info in self.event.outcome_information
            ]
        )
        if outcome_note == "":
            return None
        return outcome_note

    @property
    def implemented_by(self) -> sippy.AnyOrganization:
        is_implementer: Callable[[premis.LinkingAgentIdentifier], bool] = (
            lambda link: any([role.innerText == "implementer" for role in link.roles])
        )
        agents = (
            self.agent_map.get(link)
            for link in self.event.linking_agent_identifiers
            if is_implementer(link)
        )
        implementer_agent = next(agents)
        return sippy.Organization(
            identifier=implementer_agent.primary_identifier.value,
            pref_label=sippy.LangStr(nl=implementer_agent.name.innerText),
        )

    @property
    def executed_by(self) -> sippy.SoftwareAgent | None:
        is_executer: Callable[[premis.LinkingAgentIdentifier], bool] = lambda link: any(
            [role.innerText == "executer" for role in link.roles]
        )
        agents = (
            self.agent_map.get(link)
            for link in self.event.linking_agent_identifiers
            if is_executer(link)
        )
        executer_agent = next(agents, None)
        if executer_agent is None:
            return None

        return sippy.SoftwareAgent(
            id=executer_agent.primary_identifier.value,
            name=sippy.LangStr(nl=executer_agent.name.innerText),
            model=None,
            serial_number=None,
            version=None,
        )

    @property
    def instrument(self) -> list[sippy.HardwareAgent]:
        is_instrument: Callable[[premis.LinkingAgentIdentifier], bool] = (
            lambda link: any([role.innerText == "instrument" for role in link.roles])
        )
        instrument_agents = [
            self.agent_map.get(link)
            for link in self.event.linking_agent_identifiers
            if is_instrument(link)
        ]
        return [
            sippy.HardwareAgent(
                name=sippy.LangStr(nl=ag.name.innerText),
                model=None,
                serial_number=None,
                version=None,
            )
            for ag in instrument_agents
        ]

    @property
    def was_associated_with(self) -> list[sippy.Agent]:
        has_no_roles: Callable[[premis.LinkingAgentIdentifier], bool] = (
            lambda link: len(link.roles) == 0
        )
        associated_agents = [
            self.agent_map.get(link)
            for link in self.event.linking_agent_identifiers
            if has_no_roles(link)
        ]

        # TODO: could also be an organization
        return [
            sippy.Person(
                id=agent.uuid.value,
                name=sippy.LangStr(nl=agent.name.innerText),
                birth_date=None,
                death_date=None,
            )
            for agent in associated_agents
        ]

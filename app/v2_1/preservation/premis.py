from typing import cast
from functools import partial, cached_property
from itertools import chain

from pydantic.dataclasses import dataclass

import sippy

from app.v2_1.namespaces import haObj
from ..models import premis

from .premis_utils import AgentMap, ObjectMap, TemporaryObject
from . import film

from ..utils import ParseException


from ..level import Level


@dataclass
class PreservationTransformer:
    """
    Transform premis SIP information into SIP.py objects (IntellectualEntity, DigitalRepresentation, Events, etc...)
    """

    package: Level
    representations: list[Level]

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
            sippy.LocalIdentifier(value=id.value.text, type=haObj[id.type.text])
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
            _ = self.package.premis_info.representation
        except StopIteration:
            return None
        parser = CarrierTransformer(self.package)
        return parser.parse_carrier_representation()

    def get_digital_representations(self) -> list[sippy.DigitalRepresentation]:
        """
        Extract the digital representation from the representation PREMIS files.
        """
        return [
            DigitalTransformer(repr).parse_digital_representation()
            for repr in self.representations
        ]

    @property
    def events(self) -> list[sippy.Event]:
        tf = EventTransformer(self)
        return [tf.parse(event) for event in self.package.premis_info.events]

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
class DigitalTransformer:
    """
    Transform a premis SIP representation into a SIP.py DigitalRepresentation
    """

    representation_level: Level

    def is_digital_relationship(self, relationship: premis.Relationship) -> bool:
        # TODO: represents also contains carrier representation
        return relationship.sub_type.text in sippy.Represents

    def parse_digital_representation(self) -> sippy.DigitalRepresentation:
        premis_repr = self.representation_level.premis_info.representation
        files = [
            self.parse_file(file)
            for file in self.representation_level.premis_info.files
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
            name=sippy.UniqueLangStrings.codes(nl="Digital Representation"),
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
        relative_path = self.representation_level.relative_path

        premis_representation = self.representation_level.premis_info.representation
        representation_identifier = premis_representation.uuid.value.text

        return sippy.File(
            id=file.uuid.value.text,
            is_included_in=[sippy.Reference(id=representation_identifier)],
            size=sippy.NonNegativeInt(value=int(size.value)),
            name=sippy.UniqueLangStrings.codes(nl="File"),
            original_name=original_name,
            fixity=sippy.Fixity(
                id=sippy.uuid4(),
                type=map_fixity_digest_algorithm_to_uri(
                    fixity.message_digest_algorithm.text
                ),
                value=fixity.message_digest.text,
                creator=[],
            ),
            format=sippy.FileFormat(id=map_file_format_to_uri(format)),
            stored_at=sippy.StorageLocation(
                storage_medium=[],
                file_path=str(relative_path.joinpath("data").joinpath(original_name)),
            ),
        )


@dataclass
class CarrierTransformer:
    """
    Transform the carrier representation in the package premis file into a SIP.py CarrierRepresentation.
    """

    package_level: Level

    def is_carrier_relationship(self, relationship: premis.Relationship) -> bool:
        return relationship.sub_type.text == "is carrier copy of"

    def parse_carrier_representation(self) -> sippy.CarrierRepresentation:
        return sippy.CarrierRepresentation(
            id=self.premis_carrier.uuid.value.text,
            represents=self.reference_to_entity,
            is_carrier_copy_of=self.reference_to_entity,
            stored_at=[
                *self.image_reels,
                *self.audio_reels,
            ],
            has_missing_audio_reels=self.carrier_significant_properties.has_missing_audio_reels,
            has_missing_image_reels=self.carrier_significant_properties.has_missing_image_reels,
            number_of_reels=self.number_of_reels,
            number_of_missing_audio_reels=None,
            number_of_missing_image_reels=None,
            number_of_audio_tracks=None,
            number_of_audio_channels=None,
            name=sippy.UniqueLangStrings.codes(
                nl=f"Carrier representation of {self.reference_to_entity.id}"
            ),
        )

    @property
    def number_of_reels(self) -> sippy.NonNegativeInt | None:
        n_reels = self.carrier_significant_properties.number_of_reels
        return sippy.NonNegativeInt(value=n_reels) if n_reels is not None else None

    def map_medium_to_uri(self, medium: str) -> str:
        return "https://data.hetarchief.be/id/carrier-type/" + medium

    def audio_reel(self, audio_reel: film.AudioReel) -> sippy.AudioReel:
        return sippy.AudioReel(**self.physical_carrier(audio_reel).keywords)

    def physical_carrier(
        self, physical_carrier: film.ImageReel | film.AudioReel
    ) -> partial[sippy.PhysicalCarrier]:
        return partial(
            sippy.PhysicalCarrier,
            storage_medium=sippy.StorageMedium(
                id=self.map_medium_to_uri(physical_carrier.medium)
            ),
            description=None,
            width=None,
            height=None,
            depth=None,
            material=physical_carrier.material,
            material_extent=None,
            identifier=physical_carrier.identifier,
            preservation_problem=[
                sippy.Concept(
                    id=sippy.uuid4(),
                    pref_label=sippy.UniqueLangStrings.codes(nl=p),
                )
                for p in physical_carrier.preservation_problems
            ],
        )

    def image_reel(self, image_reel: film.ImageReel) -> sippy.ImageReel:
        return sippy.ImageReel(
            **self.physical_carrier(image_reel).keywords,
            file_path=None,
            name=sippy.UniqueLangStrings.codes(nl=f"Image Reel {image_reel.medium}"),
            coloring_type=[self.coloring_type(c) for c in image_reel.coloring_type],
            has_captioning=self.has_captioning(image_reel.has_captioning),
            aspect_ratio=image_reel.aspect_ratio,
        )

    @property
    def image_reels(self) -> list[sippy.ImageReel]:
        image_reels = chain.from_iterable(
            stored_at.image_reels
            for stored_at in self.carrier_significant_properties.stored_at
        )
        return [self.image_reel(reel) for reel in image_reels]

    @property
    def audio_reels(self) -> list[sippy.AudioReel]:
        audio_reels = chain.from_iterable(
            stored_at.audio_reels
            for stored_at in self.carrier_significant_properties.stored_at
        )
        return [self.audio_reel(reel) for reel in audio_reels]

    def has_captioning(
        self, has_captioning: film.HasCaptioning | None
    ) -> list[sippy.OpenCaptions]:
        if has_captioning is None:
            return []
        return [self.open_captions(c) for c in has_captioning.open_captions]

    def open_captions(self, open_captions: film.OpenCaptions) -> sippy.OpenCaptions:
        return sippy.OpenCaptions(in_language=open_captions.in_languages)

    def coloring_type(self, coloring_type: str) -> sippy.URIRef[sippy.ColoringType]:
        iri = "https://data.hetarchief.be/id/color-type/" + coloring_type
        coloring_types = [c for c in sippy.ColoringType]
        if iri not in coloring_types:
            raise ParseException(
                f"Unkown coloring type {coloring_type}. Coloring type must be one of {coloring_types}"
            )
        return sippy.URIRef(id=sippy.ColoringType(iri))

    @property
    def premis_carrier(self) -> premis.Representation:
        return self.package_level.premis_info.representation

    @cached_property
    def carrier_significant_properties(self) -> film.CarrierSignificantProperties:
        significant_properties = next(iter(self.premis_carrier.significant_properties))
        extension = next(iter(significant_properties.extension))
        return film.CarrierSignificantProperties.from_xml_tree(extension)

    @property
    def reference_to_entity(self) -> sippy.Reference:
        relationship_to_entity = next(
            rel
            for rel in self.premis_carrier.relationships
            if self.is_carrier_relationship(rel)
        )
        return sippy.Reference(id=relationship_to_entity.related_object_uuid)


class EventTransformer:
    """
    Transform a premis SIP Event into a SIP.py Event
    """

    def __init__(self, structural: "PreservationTransformer") -> None:
        # Events can referece agents and objects from anywhere in the SIP
        # These map the refences to the actual agents and objects
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
            event_detail_extension={},
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
            pref_label=sippy.UniqueLangStrings.codes(nl=implementer_agent.name.text),
            name=sippy.UniqueLangStrings.codes(nl=implementer_agent.name.text),
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
            name=sippy.UniqueLangStrings.codes(nl=executer_agent.name.text),
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
                name=sippy.UniqueLangStrings.codes(nl=ag.name.text),
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
                name=sippy.UniqueLangStrings.codes(nl=agent.name.text),
                birth_date=None,
                death_date=None,
            )
            for agent in associated_agents
        ]

    def map_event_type_to_uri(self, type: str) -> str:
        return "https://data.hetarchief.be/id/event-type/" + type

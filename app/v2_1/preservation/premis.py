from typing import Self
from functools import partial
from pathlib import Path

from pydantic.dataclasses import dataclass

import sippy
import eark_models.premis.v3_0 as premis_

from app.v2_1.preservation.events import Event2Sippy

from ..mets import METS, parse_mets
from ..utils import ParseException


@dataclass
class StructuralInfo:
    """Structural metadata of either the package level or the representation level."""

    relative_path: Path
    mets: METS
    premis: premis_.Premis

    @classmethod
    def from_path(cls, path: Path, sip_path: Path) -> Self:
        mets_path = path.joinpath("METS.xml")
        mets = parse_mets(mets_path)

        return cls(
            mets=mets,
            premis=StructuralInfo.parse_premis(mets),
            relative_path=path.relative_to(sip_path),
        )

    @staticmethod
    def parse_premis(mets: METS) -> premis_.Premis:
        if mets.administrative_metadata is None:
            raise ParseException("No PREMIS found.")
        return premis_.Premis.from_xml(mets.administrative_metadata)


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
        entity = self.package.premis.entity
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
            carrier = self.package.premis.representation
        except StopIteration:
            # No carrier was found
            return None

        entity_rel = next(
            rel
            for rel in carrier.relationships
            if rel.sub_type.text == "is carrier copy of"
        )
        entity_id = entity_rel.related_object_uuid

        return sippy.CarrierRepresentation(
            id=carrier.uuid.value.text,
            represents=sippy.Reference(id=entity_id),
            is_carrier_copy_of=sippy.Reference(id=entity_id),
            stored_at=[],  # TODO: the SIP spec must be finalized before this part can be parsed
        )

    def get_digital_representations(self) -> list[sippy.DigitalRepresentation]:
        """
        Extract the digital representation from the representation PREMIS files.
        """
        digital_representations: list[sippy.DigitalRepresentation] = []
        for representation in self.representations:
            repr = representation.premis.representation
            files = [
                parse_file(file, repr.uuid.value.text, representation.relative_path)
                for file in representation.premis.files
            ]
            relationship_to_entity = next(
                (
                    rel
                    for rel in repr.relationships
                    if rel.sub_type.text in sippy.Represents
                )
            )

            is_x_copy = lambda x: relationship_to_entity.sub_type.text == x
            is_master = is_x_copy(sippy.Represents.is_master_copy_of)
            is_mezzanine = is_x_copy(sippy.Represents.is_mezzanine_copy_of)
            is_access = is_x_copy(sippy.Represents.is_access_copy_of)
            is_transcription = is_x_copy(sippy.Represents.is_transcription_copy_of)
            reference = sippy.Reference(id=relationship_to_entity.related_object_uuid)

            digital = sippy.DigitalRepresentation(
                id=repr.uuid.value.text,
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
        sippify = Event2Sippy(self)
        return [sippify.parse(event) for event in self.package.premis.events]

    @property
    def premis_agents(self) -> list[sippy.PremisAgent]:
        return [
            sippy.PremisAgent(
                identifier=agent.uuid.value.text,
                name=agent.name.text,
                type=agent.type.text,
            )
            for agent in self.package.premis.agents
            if any(id.is_uuid for id in agent.identifiers)
        ]


def parse_file(file: premis_.File, repr_id: str, relative_path: Path) -> sippy.File:
    size = next((c.size for c in file.characteristics if c.size is not None))
    fixity = next(iter(next(c.fixity for c in file.characteristics)))
    format = next(iter(next(c.format for c in file.characteristics)))

    if file.original_name is None:
        raise ParseException()

    original_name = file.original_name.text

    return sippy.File(
        id=file.uuid.value.text,
        is_included_in=[sippy.Reference(id=repr_id)],
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


def map_fixity_digest_algorithm_to_uri(algorithm: str) -> str:
    if algorithm == "md5" or algorithm == "MD5":
        return (
            "http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions/md5"
        )

    raise ParseException(f"Unknown fixity message digest algorithm {algorithm}")


def map_file_format_to_uri(format: premis_.Format) -> str:
    if not format.registry:
        raise ParseException("Format registry must be present")
    if format.registry.name.text != "PRONOM":
        raise ParseException("Only the PRONOM format registry is supported")

    format_key = format.registry.key.text
    return "https://www.nationalarchives.gov.uk/pronom/" + format_key


def is_digital_relationship(rel: premis_.Relationship) -> bool:
    return (
        rel.sub_type.text in sippy.IsRepresentedBy
        and rel.sub_type.text != sippy.IsRepresentedBy.has_carrier_copy
    )


def filter_digital_relationships_by_name(
    relationships: list[premis_.Relationship], name: str
) -> list[sippy.Reference]:
    return [
        sippy.Reference(id=rel.related_object_uuid)
        for rel in relationships
        if is_digital_relationship(rel) and rel.sub_type.text == name
    ]

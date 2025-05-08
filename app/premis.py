from typing import Literal
from pydantic_xml import BaseXmlModel, attr, element
from app.utils import ns


class PremisBaseModel(BaseXmlModel, ns="premis", nsmap=ns):
    pass


class StringPlusAuthority(BaseXmlModel):
    authority: str | None = attr(default=None)
    authority_uri: str | None = attr(name="authorityURI", default=None)
    innerText: str
    value_uri: str | None = attr(name="valueURI", default=None)


########## Object ##########


class ObjectIdentifier(PremisBaseModel, tag="objectIdentifier"):
    type: StringPlusAuthority = element(tag="objectIdentifierType", ns="premis")
    value: str = element(tag="objectIdentifierValue", ns="premis")
    simple_link: str | None = attr(name="simpleLink", default=None)

    @property
    def is_uuid(self):
        return self.type.innerText == "UUID"

    @property
    def is_pid(self):
        return self.type.innerText == "MEEMOO-PID"

    @property
    def is_primary_identifier(self):
        return self.type.innerText == "MEEMOO-LOCAL-ID"

    @property
    def is_local_identifier(self):
        return (
            self.type.innerText != "UUID"
            and self.type.innerText != "MEEMOO-PID"
            and self.type.innerText != "MEEMOO-LOCAL-ID"
        )


class Fixity(PremisBaseModel, tag="fixity"):
    message_digest_algorithm: StringPlusAuthority = element(
        tag="messageDigestAlgorithm", ns="premis"
    )
    message_digest: str = element(tag="messageDigest", ns="premis")
    message_digest_originator: StringPlusAuthority | None = element(
        tag="messageDigestOriginator", ns="premis", default=None
    )


class FormatDesignation(PremisBaseModel, tag="formatDesignation"):
    name: StringPlusAuthority = element(tag="formatName", ns="premis")
    version: str | None = element(tag="formatVersion", ns="premis", default=None)


class FormatRegistry(PremisBaseModel, tag="formatRegistry"):
    name: StringPlusAuthority = element(tag="formatRegistryName", ns="premis")
    key: StringPlusAuthority = element(tag="formatRegistryKey", ns="premis")
    role: StringPlusAuthority | None = element(
        tag="formatRegistryRole", ns="premis", default=None
    )
    simple_link: str | None = attr(name="simpleLink", default=None)


class Format(PremisBaseModel, tag="format"):
    designation: FormatDesignation | None = element(default=None)
    registry: FormatRegistry | None = element(default=None)
    note: list[str] = element(tag="formatNote", ns="premis", default_factory=list)


class ObjectCharacteristics(PremisBaseModel, tag="objectCharacteristics"):
    # composition_level: ...
    fixity: list[Fixity] = element(default_factory=list)
    size: int | None = element(tag="size", ns="premis", default=None)
    format: list[Format] = element(min_length=1)
    # creating_application: ...
    # inhibitors: ...
    # object_characteristics_extension: ...


class OriginalName(PremisBaseModel, tag="orignalName"):
    value: str
    simple_link: str | None = attr(name="simpleLink", default=None)


class RelatedObjectIdentifier(PremisBaseModel, tag="relatedObjectIdentifier"):
    type: StringPlusAuthority = element(tag="relatedObjectIdentifierType", ns="premis")
    value: str = element(tag="relatedObjectIdentifierValue", ns="premis")
    # sequence: ... | None
    # RelObjectXmlID
    simple_link: str | None = attr(name="simpleLink", default=None)


class Relationship(PremisBaseModel, tag="relationship"):
    type: StringPlusAuthority = element(tag="relationshipType", ns="premis")
    sub_type: StringPlusAuthority = element(tag="relationshipSubType", ns="premis")
    related_object_identifier: list[RelatedObjectIdentifier] = element(min_length=1)
    # related_event_identifier: list[...] = element(default_factory=list)
    # related_environment_purpose: list[...] = element(default_factory=list)
    # related_environment_characteristic: list[...] | None = element(default=None)

    @property
    def related_object_uuid(self) -> str:
        return next(
            (
                id.value
                for id in self.related_object_identifier
                if id.type.innerText == "UUID"
            )
        )


class SignificantProperties(PremisBaseModel, tag="significantProperties"):
    type: StringPlusAuthority | None = element(
        tag="significantPropertiesType", ns="premis", default=None
    )
    value: str | None = element(
        tag="significantPropertiesValue", ns="premis", default=None
    )
    extension: list[str] = element(
        tag="significantPropertiesExtension", ns="premis", default_factory=list
    )


class Storage(PremisBaseModel, tag="storage"):
    # content_location: ... | None
    storage_medium: StringPlusAuthority | None = element(
        tag="storageMedium", ns="premis", default=None
    )


class File(PremisBaseModel, tag="object"):
    xsi_type: Literal["premis:file"] = attr(name="type", ns="xsi")

    identifiers: list[ObjectIdentifier] = element(min_length=1)
    # preservation_levels: list[PreservationLevel] = element(default_factory=list)
    significant_properties: list[SignificantProperties] = element(default_factory=list)
    characteristics: list[ObjectCharacteristics] = element(min_length=1)
    original_name: OriginalName | None = element(default=None)
    storages: list[Storage] = element(default_factory=list)
    # signature_informations: list[...]
    relationships: list[Relationship] = element(default_factory=list)
    # linking_event_identifiers: list[...]
    # linking_rights_statement_identifiers: list[...]

    # xml_id: ... = attr()
    # version: Literal["version3"] = attr()

    @property
    def uuid(self):
        return next((id for id in self.identifiers if id.is_uuid))


class Representation(PremisBaseModel, tag="object"):
    xsi_type: Literal["premis:representation"] = attr(name="type", ns="xsi")

    identifiers: list[ObjectIdentifier] = element(min_length=1)
    # preservation_levels: list[PreservationLevel] = element(default_factory=list)
    significant_properties: list[SignificantProperties] = element(default_factory=list)
    original_name: OriginalName | None = element(default=None)
    storages: list[Storage] = element(default_factory=list)
    relationships: list[Relationship] = element(default_factory=list)
    # linking_event_identifiers: list[...]
    # linking_rights_statement_identifiers: list[...]

    # xml_id: ... = attr()
    # version: Literal["version3"] = attr()

    @property
    def uuid(self):
        return next((id for id in self.identifiers if id.is_uuid))


class Bitstream(PremisBaseModel, tag="object"):
    xsi_type: Literal["premis:bitstream"] = attr(name="type", ns="xsi")

    identifiers: list[ObjectIdentifier] = element(min_length=1)
    significant_properties: list[SignificantProperties] = element(default_factory=list)
    characteristics: list[ObjectCharacteristics] = element(min_length=1)
    storages: list[Storage] = element(default_factory=list)
    # signature_informations: list[...]
    relationships: list[Relationship] = element(default_factory=list)
    # linking_event_identifiers: list[...]
    # linking_rights_statement_identifiers: list[...]

    # xml_id: ... = attr()
    # version: Literal["version3"] = attr()

    @property
    def uuid(self):
        return next((id for id in self.identifiers if id.is_uuid))


class IntellectualEntity(PremisBaseModel, tag="object"):
    xsi_type: Literal["premis:intellectualEntity"] = attr(name="type", ns="xsi")

    identifiers: list[ObjectIdentifier] = element(min_length=1)
    # preservation_levels: list[PreservationLevel] = element(default_factory=list)
    significant_properties: list[SignificantProperties] = element(default_factory=list)
    original_name: OriginalName | None = element(default=None)
    # environmentFunction
    # environmentDesignation
    # environmentRegistry
    # environmentExtension
    relationships: list[Relationship] = element(default_factory=list)
    # linking_event_identifiers: list[...]
    # linking_rights_statement_identifiers: list[...]

    # xml_id: ... = attr()
    # version: Literal["version3"] = attr()

    @property
    def uuid(self):
        return next((id for id in self.identifiers if id.is_uuid))

    @property
    def pid(self):
        return next((id for id in self.identifiers if id.is_pid), None)


Object = File | Representation | IntellectualEntity | Bitstream


class LinkingObject(BaseXmlModel):
    """
    This is a utility class that does not exist in PREMIS.
    It is used for to replace `LinkingObjectIdentifiers` by the actual `Object` that is referenced.
    """

    object: Object
    roles: list[StringPlusAuthority]


########## Agent ##########


class AgentIdentifier(PremisBaseModel, tag="agentIdentifier"):
    type: StringPlusAuthority = element(tag="agentIdentifierType", ns="premis")
    value: str = element(tag="agentIdentifierValue", ns="premis")


class Agent(PremisBaseModel, tag="agent"):
    identifiers: list[AgentIdentifier] = element(min_length=1)
    name: StringPlusAuthority = element(tag="agentName", ns="premis")
    type: StringPlusAuthority = element(tag="agentType", ns="premis")


class LinkingAgent(BaseXmlModel):
    """
    This is a utility class that does not exist in PREMIS.
    It is used for to replace `LinkingAgentIdentifiers` by the actual `Agent` that is referenced.
    """

    agent: Agent
    roles: list[StringPlusAuthority]


########## Event ##########


class EventIdentifier(PremisBaseModel, tag="eventIdentifier"):
    type: StringPlusAuthority = element(tag="eventIdentifierType", ns="premis")
    value: StringPlusAuthority = element(tag="eventIdentifierValue", ns="premis")
    simple_link: str | None = attr(name="simpleLink", default=None)


class EventDetailInformation(PremisBaseModel, tag="eventDetailInformation"):
    detail: str | None = element(tag="eventDetail", ns="premis", default=None)
    # detail_extension: list[EventDetailExtension] = element(default_factory=list)


class EventOutcomeDetail(PremisBaseModel, tag="eventOutcomeDetail"):
    note: str | None = element(tag="eventOutcomeDetailNote", ns="premis", default=None)
    # extension: list[EventOutcomeExtension] = (default_factory=list)


class EventOutcomeInformation(PremisBaseModel, tag="eventOutcomeInformation"):
    outcome: StringPlusAuthority | None = element(
        tag="eventOutcome", ns="premis", default=None
    )
    outcome_detail: list[EventOutcomeDetail] = element(default_factory=list)


class LinkingAgentIdentifier(PremisBaseModel, tag="linkingAgentIdentifier"):
    type: StringPlusAuthority = element(tag="linkingAgentIdentifierType", ns="premis")
    value: str = element(tag="linkingAgentIdentifierValue", ns="premis")
    roles: list[StringPlusAuthority] = element(
        tag="linkingAgentRole", ns="premis", default_factory=list
    )

    # LinkAgentXmlID
    simple_link: str | None = attr(name="simpleLink", default=None)


class LinkingObjectIdentifier(PremisBaseModel, tag="linkingObjectIdentifier"):
    type: StringPlusAuthority = element(tag="linkingObjectIdentifierType", ns="premis")
    value: str = element(tag="linkingObjectIdentifierValue", ns="premis")
    roles: list[StringPlusAuthority] = element(
        tag="linkingObjectRole", ns="premis", default_factory=list
    )

    # LinkObjectXmlID
    simple_link: str | None = attr(name="simpleLink", default=None)


class Event(PremisBaseModel, tag="event"):
    identifier: EventIdentifier
    type: StringPlusAuthority = element(tag="eventType", ns="premis")
    datetime: str = element(tag="eventDateTime", ns="premis")
    detail_information: list[EventDetailInformation] = element(default_factory=list)
    outcome_information: list[EventOutcomeInformation] = element(default_factory=list)
    linking_agents: list[LinkingAgentIdentifier | LinkingAgent] = element(
        default_factory=list
    )
    linking_objects: list[LinkingObjectIdentifier | LinkingObject] = element(
        default_factory=list
    )

    # xml_id = attr()
    # version: Literal["version3"]


########## Premis ##########


class Premis(PremisBaseModel, tag="premis"):
    objects: list[Object] = element(default_factory=list, min_legnth=1)
    events: list[Event] = element(default_factory=list)
    agents: list[Agent] = element(default_factory=list)

    @property
    def entity(self) -> IntellectualEntity:
        """
        Returns the first object with xsi:type='intellectualEntity' in the PREMIS file.
        """
        return next(
            (obj for obj in self.objects if isinstance(obj, IntellectualEntity))
        )

    @property
    def representation(self):
        """
        Returns the first object with xsi:type='intellectualEntity' in the PREMIS file.
        """
        return next((obj for obj in self.objects if isinstance(obj, Representation)))

    @property
    def files(self):
        """
        Returns all objects with xsi:type='file' in the PREMIS file.
        """
        return [obj for obj in self.objects if isinstance(obj, File)]

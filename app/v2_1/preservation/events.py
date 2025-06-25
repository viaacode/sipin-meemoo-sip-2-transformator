from typing import cast, Callable, TYPE_CHECKING

import dateutil.parser
from pydantic import BaseModel

import sippy

from ..models import premis as premis_

from .premis_utils import AgentMap, ObjectMap, TemporaryObject
from ..utils import ParseException

if TYPE_CHECKING:
    from .premis import SIPStructuralInfo


class Event2Sippy:
    def __init__(self, structural: "SIPStructuralInfo") -> None:
        self.agent_map = AgentMap.create(structural)
        self.object_map = ObjectMap.create(structural)

    def parse(self, event: premis_.Event) -> sippy.Event:
        type = cast(sippy.EventClass, map_event_type_to_uri(event.type.text))
        datetime = dateutil.parser.parse(event.datetime.text)

        return sippy.Event(
            id=event.identifier.value.text,
            type=type,
            was_associated_with=self.was_associated_with(event),
            started_at_time=sippy.DateTime(value=datetime),
            ended_at_time=sippy.DateTime(value=datetime),
            implemented_by=self.implemented_by(event),
            note=self.note(event),
            outcome=self.outcome(event),
            outcome_note=self.outcome_note(event),
            executed_by=self.executed_by(event),
            source=self.source(event),
            result=self.result(event),
            instrument=self.instrument(event),
        )

    def result(self, event: premis_.Event) -> list[sippy.Reference | sippy.Object]:
        is_result: Callable[[premis_.LinkingObjectIdentifier], bool] = lambda link: any(
            (role.text == "outcome" for role in link.roles)
        )
        result = [
            self.object_map.get(link)
            for link in event.linking_object_identifiers
            if is_result(link)
        ]

        refs = [
            sippy.Reference(id=obj.uuid.value.text)
            for obj in result
            if isinstance(obj, premis_.Object)
        ]

        objects = [
            sippy.Object(id=obj.uuid.value.text)
            for obj in result
            if isinstance(obj, TemporaryObject)
        ]

        return refs + objects

    def source(self, event: premis_.Event) -> list[sippy.Reference]:
        is_source: Callable[[premis_.LinkingObjectIdentifier], bool] = lambda link: any(
            (role.text == "source" for role in link.roles)
        )
        source_objects = [
            self.object_map.get(link)
            for link in event.linking_object_identifiers
            if is_source(link)
        ]
        return [sippy.Reference(id=obj.uuid.value.text) for obj in source_objects]

    def note(self, event: premis_.Event) -> str | None:
        details = [info.detail.text for info in event.detail_information if info.detail]
        if len(details) == 0:
            return None
        return "\\n".join(details)

    def outcome(self, event: premis_.Event) -> sippy.URIRef[sippy.EventOutcome] | None:
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

    def outcome_note(self, event: premis_.Event) -> str | None:
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

    def implemented_by(self, event: premis_.Event) -> sippy.AnyOrganization:
        is_implementer: Callable[[premis_.LinkingAgentIdentifier], bool] = (
            lambda link: any([role.text == "implementer" for role in link.roles])
        )
        agents = (
            self.agent_map.get(link)
            for link in event.linking_agent_identifiers
            if is_implementer(link)
        )
        implementer_agent = next(agents)
        return sippy.Organization(
            identifier=implementer_agent.primary_identifier.value.text,
            pref_label=sippy.LangStr(nl=implementer_agent.name.text),
        )

    def executed_by(self, event: premis_.Event) -> sippy.SoftwareAgent | None:
        is_executer: Callable[[premis_.LinkingAgentIdentifier], bool] = (
            lambda link: any([role.text == "executer" for role in link.roles])
        )
        agents = (
            self.agent_map.get(link)
            for link in event.linking_agent_identifiers
            if is_executer(link)
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

    def instrument(self, event: premis_.Event) -> list[sippy.HardwareAgent]:
        is_instrument: Callable[[premis_.LinkingAgentIdentifier], bool] = (
            lambda link: any([role.text == "instrument" for role in link.roles])
        )
        instrument_agents = [
            self.agent_map.get(link)
            for link in event.linking_agent_identifiers
            if is_instrument(link)
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

    def was_associated_with(self, event: premis_.Event) -> list[sippy.Agent]:
        has_no_roles: Callable[[premis_.LinkingAgentIdentifier], bool] = (
            lambda link: len(link.roles) == 0
        )
        associated_agents = [
            self.agent_map.get(link)
            for link in event.linking_agent_identifiers
            if has_no_roles(link)
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


def map_event_type_to_uri(type: str) -> str:
    return "https://data.hetarchief.be/id/event-type/" + type

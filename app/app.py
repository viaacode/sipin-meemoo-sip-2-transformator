from typing import Any, Callable

from cloudevents.events import Event, EventAttributes, EventOutcome, PulsarBinding
from viaa.configuration import ConfigParser
from viaa.observability import logging

from app.services.pulsar import PulsarClient
import app.v2_1 as v2_1

import _pulsar

APP_NAME = "sipin-meemoo-sip-2-transformator"


class EventListener:
    """
    EventListener is responsible for listening to Pulsar events and processing them.
    """

    def __init__(self, timeout_ms: int | None = None):
        """
        Initializes the EventListener with configuration, logging, and Pulsar client.
        """
        config_parser = ConfigParser()
        self.log = logging.get_logger(__name__, config=config_parser)
        self.pulsar_client = PulsarClient(timeout_ms)
        self.running = False

    def handle_incoming_message(self, event: Event):
        """
        Handles an incoming Pulsar event.

        Args:
            event (Event): The incoming event to process.
        """
        is_event_success = event.has_successful_outcome()
        is_validation_success = event.get_data()["is_valid"]
        if not is_event_success or not is_validation_success:
            self.log.info(f"Dropping non successful event: {event.get_data()}")
            return

        subject = event.get_attributes()["subject"]
        self.log.info(f"Start handling of {subject}.")
        path = event.get_data()["sip_path"]
        # TODO: Sip profile is not yet implemented in the event. For now use the hardcoded value below.
        # profile = event.get_data()["sip_profile"]

        # TODO: remove hardcoded profile - only necessairy for demo
        profile = "https://data.hetarchief.be/id/sip/2.1/film"

        transformator_fn = self.get_sip_transformator(profile)
        data = transformator_fn(path)
        data["is_valid"] = True
        self.produce_success_event(event, data)

    def get_sip_transformator(self, profile: str) -> Callable[[str], dict[str, Any]]:
        parts = profile.split("/")
        version = parts[-2]

        match version:
            case "2.1":
                return v2_1.transform_sip
            case _:
                raise ValueError("Invalid SIP profile found in received message.")

    def produce_success_event(self, event: Event, data: dict[str, Any]):
        path = event.get_data()["sip_path"]
        produced_event = Event(
            attributes=EventAttributes(
                datacontenttype="application/cloudevents+json; charset=utf-8",
                correlation_id=event.correlation_id,
                source=APP_NAME,
                subject=path,
                outcome=EventOutcome.SUCCESS,
            ),
            data=data,
        )

        self.pulsar_client.produce_event(
            self.pulsar_client.pulsar_config["producer_topic"], produced_event
        )

    def produce_fail_event(self, event: Event, exception: Exception) -> None:
        subject = event.get_attributes()["subject"]
        produced_event = Event(
            attributes=EventAttributes(
                datacontenttype="application/cloudevents+json; charset=utf-8",
                correlation_id=event.correlation_id,
                source=APP_NAME,
                subject=subject,
                outcome=EventOutcome.FAIL,
            ),
            data={
                "message": str(exception),
                "is_valid": False,  # type: ignore
            },
        )

        self.pulsar_client.produce_event(
            self.pulsar_client.pulsar_config["producer_topic"], produced_event
        )

    def start_listening(self):
        """
        Starts listening for incoming messages from the Pulsar topic.
        """
        self.running = True
        while self.running:
            try:
                msg = self.pulsar_client.receive()
            except _pulsar.Timeout:
                continue

            event = PulsarBinding.from_protocol(msg)  # type: ignore
            try:
                self.handle_incoming_message(event)
                self.pulsar_client.acknowledge(msg)
            except Exception as e:
                # Catch and log any errors during message processing
                self.log.error(f"Error: {e}")
                self.pulsar_client.acknowledge(msg)
                self.produce_fail_event(event, e)

        self.pulsar_client.close()

from cloudevents.events import Event, EventAttributes, PulsarBinding
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
        is_validation_success = event.get_data()["outcome"] != "success"
        if not is_event_success or not is_validation_success:
            self.log.info(f"Dropping non successful event: {event.get_data()}")
            return

        self.log.info(f"Start handling of {event.get_attributes()['subject']}.")
        path = event.get_data()["sip_path"]
        sip = v2_1.parse_sip(path)
        jsonld = sip.to_jsonld()

        produced_event = Event(
            attributes=EventAttributes(
                datacontenttype="application/cloudevents+json; charset=utf-8",
            ),
            data={
                "metadata_format": "jsonld",
                "metadata": jsonld,
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

            try:
                event = PulsarBinding.from_protocol(msg)  # type: ignore
                self.handle_incoming_message(event)
                self.pulsar_client.acknowledge(msg)
            except Exception as e:
                # Catch and log any errors during message processing
                self.log.error(f"Error: {e}")
                self.pulsar_client.negative_acknowledge(msg)

        self.pulsar_client.close()

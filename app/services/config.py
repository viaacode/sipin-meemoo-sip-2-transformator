from typing import Self
from dataclasses import dataclass
import os


@dataclass
class PulsarConfig:
    host: str
    port: int
    consumer_topic: str
    producer_topic: str

    @classmethod
    def from_env(cls) -> Self:
        host = os.environ.get("PULSAR_HOST")
        port = os.environ.get("PULSAR_PORT")
        consumer_topic = os.environ.get("PULSAR_CONSUMER_TOPIC")
        producer_topic = os.environ.get("PULSAR_PRODUCER_TOPIC")

        if (
            host is None
            or port is None
            or consumer_topic is None
            or producer_topic is None
        ):
            raise ValueError(
                "The following ENV vars must be set: PULSAR_HOST, PULSAR_PORT, PULSAR_CONSUMER_TOPIC, PULSAR_PRODUCER_TOPIC"
            )

        return cls(
            host=host,
            port=int(port),
            consumer_topic=consumer_topic,
            producer_topic=producer_topic,
        )

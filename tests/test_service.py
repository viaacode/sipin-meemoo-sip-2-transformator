from threading import Thread
from queue import Queue
from time import sleep
import json

from cloudevents.events import EventOutcome
import pytest
from testcontainers.core.container import DockerContainer
import pulsar

from cloudevents import PulsarBinding

from app.app import EventListener
from app.services.config import PulsarConfig


pulsar_config = PulsarConfig.from_env()

pulsar_container = (
    DockerContainer("apachepulsar/pulsar")
    .with_command("bin/pulsar standalone")
    .with_bind_ports(6650, pulsar_config.port)
)


@pytest.fixture(scope="module", autouse=True)
def setup(request: pytest.FixtureRequest):
    pulsar_container.start()

    def remove_container():
        pulsar_container.stop()

    request.addfinalizer(remove_container)

    sleep(3)
    namespace = pulsar_config.consumer_topic.rsplit("/", maxsplit=1)[0]
    if namespace.startswith("persistent://"):
        namespace = namespace[13:]
    code, result = pulsar_container.exec(f"pulsar-admin namespaces create {namespace}")
    print(result)
    assert code == 0
    code, result = pulsar_container.exec(
        f"pulsar-admin topics create {pulsar_config.consumer_topic}"
    )
    print(result)
    assert code == 0


@pytest.fixture
def client() -> pulsar.Client:
    return pulsar.Client(f"pulsar://{pulsar_config.host}:{pulsar_config.port}")


@pytest.fixture
def producer(request: pytest.FixtureRequest, client: pulsar.Client) -> pulsar.Producer:
    producer = client.create_producer(pulsar_config.consumer_topic)

    def remove_producer():
        producer.close()

    request.addfinalizer(remove_producer)
    return producer


@pytest.fixture
def consumer(request: pytest.FixtureRequest, client: pulsar.Client) -> pulsar.Consumer:
    consumer = client.subscribe(pulsar_config.producer_topic, "test_subscriber")

    def remove_producer():
        consumer.close()

    request.addfinalizer(remove_producer)
    return consumer


def test_pulsar_container_running():
    exit_code, _ = pulsar_container.exec("pulsar version")
    assert exit_code == 0


def test_event_listener():
    event_listener = EventListener(timeout_ms=500)

    def task():
        sleep(1)
        event_listener.running = False

    thread = Thread(target=task)
    thread.start()
    event_listener.start_listening()
    thread.join()


def test_message(producer: pulsar.Producer, consumer: pulsar.Consumer):
    event_properties = {
        "id": "230622200554968796486122694453874671655",
        "source": "sip-validator",
        "specversion": "1.0",
        "type": "be.meemoo.sipin.bag.validate",
        "datacontenttype": "application/json",
        "subject": "/opt/sipin/unzip/AWH12931330.bag.zip",
        "time": "2022-05-18T16:08:41.356423+00:00",
        "outcome": "success",
        "correlation_id": "eac2ed9d37b4478d811daf7caa74f2db",
        "content_type": "application/cloudevents+json; charset=utf-8",
    }

    event_data = {
        "data": {
            "is_valid": True,
            "sip_path": "tests/sip-examples/2.1/film_standard_mkv/uuid-2746e598-75cd-47b5-9a3e-8df18e98bb95",
            "sip_profile": "https://data.hetarchief.be/id/sip/2.1/film",
            "message": "Path '/opt/sipin/unzip/AWH12931330.bag.zip' is a valid bag",
        },
    }

    event_listener = EventListener(timeout_ms=500)
    queue: Queue[pulsar.Message] = Queue()

    def produce():
        sleep(0.1)
        producer.send(
            json.dumps(event_data).encode("utf-8"),
            properties=event_properties,
        )
        event_listener.running = False

    def consume():
        try:
            message = consumer.receive(timeout_millis=500)
            queue.put(message)
        except pulsar.Timeout:
            pass

    producer_thread = Thread(target=produce)
    consumer_thread = Thread(target=consume)
    consumer_thread.start()
    producer_thread.start()
    event_listener.start_listening()
    producer_thread.join()
    consumer_thread.join()

    message = queue.get_nowait()
    event = PulsarBinding.from_protocol(message)  # type: ignore

    assert event.correlation_id == event_properties["correlation_id"]
    assert event.outcome == EventOutcome.SUCCESS
    assert "metadata" in event.get_data()

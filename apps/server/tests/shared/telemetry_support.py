"""Telemetry sinks used only at registered HTTP and job composition boundaries."""

from collections.abc import Generator
from contextlib import contextmanager
from fastapi.testclient import TestClient

from shifu.shared.core.interfaces.telemetry_provider import TelemetryEventInput


class RecordingTelemetry:
    def __init__(self) -> None:
        self.events: list[TelemetryEventInput] = []

    def emit(self, event: TelemetryEventInput) -> None:
        self.events.append(event)


class FailingTelemetry:
    def emit(self, event: TelemetryEventInput) -> None:
        del event
        raise RuntimeError('telemetry sink unavailable')


@contextmanager
def observe_errors(client: TestClient) -> Generator[TestClient]:
    """Reuse an already-running application while observing its safe 5xx body."""
    observer = TestClient(
        client.app, raise_server_exceptions=False, headers=dict(client.headers)
    )
    try:
        yield observer
    finally:
        observer.close()

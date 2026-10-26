"""Typed observation sink for registered HTTP and Inngest boundaries."""

import json
import os
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from inngest import (
    Context,
    ContextSync,
    Function,
    Inngest,
    JSON,
    MiddlewareSync,
    StepMemos,
)
from shifu.app import FastAPIApp
from shifu.shared.core.interfaces.telemetry_provider import TelemetryEventInput
from shifu.shared.messaging.inngest.inngest_client import InngestClient
from shifu.shared.providers.console_telemetry_provider import ConsoleTelemetryProvider


class TelemetryBoundaryFixture:
    def __init__(self, *, fail: bool = False) -> None:
        self.events: list[TelemetryEventInput] = []
        self.fail: bool = fail

    def emit(self, event: TelemetryEventInput) -> None:
        if self.fail:
            raise RuntimeError('telemetry sink unavailable')
        self.events.append(cast('TelemetryEventInput', dict(event)))


# The following factory is used only by disposable Inngest tests. It composes
# production routes/jobs, and adds deterministic faults at infrastructure seams.


def _control_path() -> Path:
    return Path(os.environ['SHIFU_TEST_TELEMETRY_CONTROL'])


def _control() -> str:
    try:
        return _control_path().read_text()
    except FileNotFoundError:
        return ''


class _ControlledJobTelemetry:
    def __init__(self) -> None:
        self._console: ConsoleTelemetryProvider = ConsoleTelemetryProvider(
            service='shifu-api', environment='local', version='telemetry-boundary-test'
        )

    def emit(self, event: TelemetryEventInput) -> None:
        # Observe sanitized telemetry independently of console formatting. The
        # journal belongs to this fixture process and never contains payloads.
        with _control_path().with_suffix('.jsonl').open('a') as journal:
            journal.write(json.dumps(event) + '\n')
        if _control() == 'collector-failure' and event['event'] == 'job.started':
            raise RuntimeError('telemetry sink unavailable')
        self._console.emit(event)


class _UnavailableEventMapping(Mapping[str, JSON]):
    """An infrastructure mapping failure before any job step or database access."""

    def __getitem__(self, _key: str) -> JSON:
        raise RuntimeError('boundary mapping failure')

    def __iter__(self) -> Iterator[str]:
        raise RuntimeError('boundary mapping failure')

    def __len__(self) -> int:
        return 1


class _ControlledMappingMiddleware(MiddlewareSync):
    def transform_input(
        self,
        ctx: Context | ContextSync,
        function: Function[object],
        steps: StepMemos,
    ) -> None:
        del steps
        # Only this test process and this registered function receive the fault.
        # A retry reloads the original canonical event from real Inngest storage.
        if (
            function.local_id == 'communication-deliver'
            and _control() == 'mapping-failure'
        ):
            ctx.event.data = _UnavailableEventMapping()


def create_telemetry_job_app() -> FastAPI:
    create_client = InngestClient.create

    def controlled_client() -> object:
        client = cast('Inngest', create_client())
        # The same real client serves async callbacks and synchronous outbox
        # sends. Sync middleware works in both SDK execution modes.
        client.add_middleware(_ControlledMappingMiddleware)
        return client

    with patch.object(InngestClient, 'create', staticmethod(controlled_client)):
        return FastAPIApp.register(telemetry_provider=_ControlledJobTelemetry())


@pytest.fixture(scope='module')
def telemetry_inngest_app_target(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[tuple[str, bool]]:
    control_path = tmp_path_factory.mktemp('telemetry-jobs') / 'control'
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv('SHIFU_TEST_TELEMETRY_CONTROL', str(control_path))
        try:
            yield (
                'tests.fixtures.telemetry_boundary_fixture:create_telemetry_job_app',
                True,
            )
        finally:
            control_path.unlink(missing_ok=True)


def read_job_telemetry(
    runtime_environment: dict[str, str] | None,
) -> list[dict[str, object]]:
    assert runtime_environment is not None
    journal = Path(runtime_environment['SHIFU_TEST_TELEMETRY_CONTROL']).with_suffix(
        '.jsonl'
    )
    if not journal.exists():
        return []
    events: list[dict[str, object]] = []
    for line in journal.read_text().splitlines():
        try:
            value: object = json.loads(line)
        except json.JSONDecodeError:
            continue  # The writer may be appending its final line concurrently.
        if isinstance(value, dict):
            events.append(cast('dict[str, object]', value))
    return events

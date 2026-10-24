import asyncio
from types import SimpleNamespace
from typing import cast

import pytest
from inngest import Context

from shifu.shared.core.interfaces.telemetry_provider import TelemetryEventInput
from shifu.shared.messaging.inngest.job_lifecycle_telemetry import (
    job_lifecycle_telemetry,
)


class _TelemetrySink:
    def __init__(self) -> None:
        self.events: list[TelemetryEventInput] = []

    def emit(self, event: TelemetryEventInput) -> None:
        self.events.append(event)


class _FailingTelemetrySink:
    def emit(self, event: TelemetryEventInput) -> None:
        del event
        raise RuntimeError('telemetry sink unavailable')


def _context(*, attempt: int = 0) -> Context:
    return cast(
        'Context',
        SimpleNamespace(
            attempt=attempt,
            run_id='run-123',
            event=SimpleNamespace(
                id='event-123',
                data={'secret': 'must-not-be-copied'},
            ),
        ),
    )


def test_job_lifecycle_uses_registration_identity_and_runtime_metadata() -> None:
    sink = _TelemetrySink()

    @job_lifecycle_telemetry(
        sink,
        function_id='identity-log-main-page-entered',
        max_attempts=3,
    )
    async def handler(context: Context) -> str:
        del context
        return 'done'

    async def invoke() -> str:
        return await handler(_context(attempt=1))

    assert asyncio.run(invoke()) == 'done'
    assert [event['event'] for event in sink.events] == [
        'job.started',
        'job.completed',
    ]
    for event in sink.events:
        assert event.get('job') == 'identity.log_main_page_entered'
        assert event.get('run_id') == 'run-123'
        assert event.get('event_id') == 'event-123'
        assert event.get('attempt') == 2
        assert 'secret' not in event


def test_job_lifecycle_emits_failure_and_retry_without_masking_error() -> None:
    sink = _TelemetrySink()

    @job_lifecycle_telemetry(
        sink,
        function_id='communication-deliver',
        max_attempts=3,
    )
    async def handler(context: Context) -> None:
        del context
        raise RuntimeError('business failure')

    async def invoke() -> None:
        await handler(_context())

    with pytest.raises(RuntimeError, match='business failure'):
        asyncio.run(invoke())

    assert [event['event'] for event in sink.events] == [
        'job.started',
        'job.failed',
        'job.retrying',
    ]
    assert sink.events[1].get('error_code') == 'job_failed'
    assert sink.events[1].get('exception_type') == 'RuntimeError'
    assert sink.events[2].get('result') == 'retry'


def test_telemetry_provider_failure_does_not_change_job_result() -> None:
    sink = _FailingTelemetrySink()

    @job_lifecycle_telemetry(
        sink,
        function_id='identity-log-main-page-entered',
        max_attempts=1,
    )
    async def handler(context: Context) -> str:
        del context
        return 'done'

    async def invoke() -> str:
        return await handler(_context())

    assert asyncio.run(invoke()) == 'done'

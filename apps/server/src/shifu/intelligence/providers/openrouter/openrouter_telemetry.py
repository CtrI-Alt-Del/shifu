"""Safe, best-effort telemetry helpers for OpenRouter calls."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from shifu.shared.core.interfaces.telemetry_provider import (
        TelemetryErrorCode,
        TelemetryEventInput,
        TelemetryEventName,
        TelemetryResult,
        TelemetryProvider,
    )


def emit_openrouter_event(
    telemetry_provider: TelemetryProvider | None,
    *,
    event: TelemetryEventName,
    result: TelemetryResult | None = None,
    duration_ms: float | None = None,
    error_code: TelemetryErrorCode | None = None,
    exception_type: str | None = None,
) -> None:
    if telemetry_provider is None:
        return
    input_event = cast(
        'TelemetryEventInput',
        {
            'level': (
                'ERROR'
                if event == 'integration.operation.failed'
                else 'WARNING'
                if event == 'integration.operation.retrying'
                else 'INFO'
            ),
            'event': event,
            'operation': 'openrouter.generate',
            'integration': 'openrouter',
        },
    )
    if result is not None:
        input_event['result'] = result
    if duration_ms is not None:
        input_event['duration_ms'] = duration_ms
    if error_code is not None:
        input_event['error_code'] = error_code
    if exception_type is not None:
        input_event['exception_type'] = exception_type
    try:
        telemetry_provider.emit(input_event)
    except Exception:  # noqa: BLE001 - telemetry is best effort.
        return

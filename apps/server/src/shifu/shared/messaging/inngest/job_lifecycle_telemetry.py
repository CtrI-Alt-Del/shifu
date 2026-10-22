"""Best-effort lifecycle telemetry for registered Inngest functions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from time import perf_counter
from typing import TYPE_CHECKING, TypeVar, cast

from inngest import Context

if TYPE_CHECKING:
    from shifu.shared.core.interfaces.telemetry_provider import (
        TelemetryEventInput,
        TelemetryErrorCode,
        TelemetryEventName,
        TelemetryJob,
        TelemetryProvider,
        TelemetryResult,
    )


_T = TypeVar('_T')
_JobHandler = Callable[[Context], Awaitable[_T]]

_JOB_BY_FUNCTION_ID: dict[str, TelemetryJob] = {
    'gamification-recognize-skill-completed': 'gamification.recognize_skill_completed',
    'gamification-recognize-practice-day-on-diagnostic-completed': (
        'gamification.recognize_practice_day_on_diagnostic_completed'
    ),
    'gamification-recognize-practice-day-on-activity-evaluated': (
        'gamification.recognize_practice_day_on_activity_evaluated'
    ),
    'gamification-recognize-diagnostic-completed': 'gamification.recognize_diagnostic_completed',
    'gamification-recognize-competency-mastered': 'gamification.recognize_competency_mastered',
    'gamification-purge-profile-on-account-deleted': 'gamification.purge_profile_on_account_deleted',
    'gamification-create-profile-on-account-activated': 'gamification.create_profile_on_account_activated',
    'communication-cancel': 'communication.cancel_communication',
    'communication-deliver': 'communication.deliver_communication',
    'learning-evaluate-choice-activity': 'learning.evaluate_choice_activity',
    'intelligence-purge-mentor-attachments-on-account-deleted': (
        'intelligence.purge_mentor_attachments_on_account_deleted'
    ),
    'intelligence-purge-mentor-summaries-on-account-deleted': (
        'intelligence.purge_mentor_summaries_on_account_deleted'
    ),
    'identity-record-communication-delivery-state': (
        'identity.record_communication_delivery_state'
    ),
    'identity-log-main-page-entered': 'identity.log_main_page_entered',
    'identity-fan-out-unconfirmed-account-expiry': (
        'identity.fan_out_unconfirmed_account_expiry'
    ),
    'identity-expire-unconfirmed-account': 'identity.expire_unconfirmed_account',
}


def job_lifecycle_telemetry(
    telemetry_provider: TelemetryProvider,
    *,
    function_id: str,
    max_attempts: int,
) -> Callable[[_JobHandler[_T]], _JobHandler[_T]]:
    """Decorate one async job handler with the fixed lifecycle event set.

    ``function_id`` is the static Inngest registration identifier.  The event
    payload is intentionally never inspected: only SDK execution metadata is
    copied into telemetry.
    """

    job = _job_from_function_id(function_id)

    def decorate(handler: _JobHandler[_T]) -> _JobHandler[_T]:
        @wraps(handler)
        async def instrumented(context: Context) -> _T:
            attempt = max(context.attempt + 1, 1)
            started_at = perf_counter()
            _emit(
                telemetry_provider,
                _event(
                    event='job.started',
                    job=job,
                    context=context,
                    attempt=attempt,
                ),
            )
            try:
                result = await handler(context)
            except Exception as error:
                _emit(
                    telemetry_provider,
                    _event(
                        event='job.failed',
                        job=job,
                        context=context,
                        attempt=attempt,
                        duration_ms=_duration_ms(started_at),
                        error_code='job_failed',
                        exception_type=type(error).__name__,
                        result='failure',
                    ),
                )
                if attempt < max_attempts:
                    _emit(
                        telemetry_provider,
                        _event(
                            event='job.retrying',
                            job=job,
                            context=context,
                            attempt=attempt,
                            error_code='job_failed',
                            result='retry',
                        ),
                    )
                raise

            _emit(
                telemetry_provider,
                _event(
                    event='job.completed',
                    job=job,
                    context=context,
                    attempt=attempt,
                    duration_ms=_duration_ms(started_at),
                    result='success',
                ),
            )
            return result

        return instrumented

    return decorate


def _job_from_function_id(function_id: str) -> TelemetryJob:
    candidate = _JOB_BY_FUNCTION_ID.get(function_id)
    if candidate is None:
        raise ValueError(f'Unknown telemetry job registration: {function_id}')
    return candidate


def _event(
    *,
    event: TelemetryEventName,
    job: TelemetryJob,
    context: Context,
    attempt: int,
    duration_ms: float | None = None,
    error_code: TelemetryErrorCode | None = None,
    exception_type: str | None = None,
    result: TelemetryResult | None = None,
) -> TelemetryEventInput:
    input_event = cast(
        'TelemetryEventInput',
        {
            'level': (
                'ERROR'
                if event == 'job.failed'
                else 'WARNING'
                if event == 'job.retrying'
                else 'INFO'
            ),
            'event': event,
            'run_id': context.run_id,
            'event_id': context.event.id,
            'job': job,
            'attempt': attempt,
        },
    )
    if duration_ms is not None:
        input_event['duration_ms'] = duration_ms
    if error_code is not None:
        input_event['error_code'] = error_code
    if exception_type is not None:
        input_event['exception_type'] = exception_type
    if result is not None:
        input_event['result'] = result
    return input_event


def _duration_ms(started_at: float) -> float:
    return max((perf_counter() - started_at) * 1000, 0.0)


def _emit(telemetry_provider: TelemetryProvider, event: TelemetryEventInput) -> None:
    try:
        telemetry_provider.emit(event)
    except Exception:  # noqa: BLE001 - telemetry must not affect job behavior.
        return

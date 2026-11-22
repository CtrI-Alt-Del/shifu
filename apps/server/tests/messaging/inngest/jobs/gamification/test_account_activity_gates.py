"""Unit coverage for Gamification's active-account event barriers."""

import asyncio
import inspect
from collections.abc import Callable, Mapping
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import Mock

import pytest

from shifu.gamification.messaging.inngest.jobs import (
    CreateProfileOnAccountActivatedJob,
    RecognizeActivityXpOnActivityEvaluatedJob,
    RecognizeCompetencyMasteredJob,
    RecognizeDiagnosticCompletedJob,
    RecognizePracticeDayOnActivityEvaluatedJob,
    RecognizePracticeDayOnDiagnosticCompletedJob,
    RecognizeSkillCompletedJob,
)
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.interfaces import AccountActivityProvider
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider

if TYPE_CHECKING:
    from inngest import Inngest


class _DeniedActivityScope:
    async def __aenter__(self) -> None:
        raise AuthorizationError

    async def __aexit__(self, *_: object) -> None:
        return None


class _RegistrationFake:
    def create_function(self, **_: object) -> Callable[[Callable[..., Any]], Any]:
        return lambda function: function


class _StepRunner:
    def __init__(self) -> None:
        self.outputs: dict[str, object] = {}

    async def run(
        self, step_name: str, callback: Callable[..., Any], *args: Any
    ) -> Any:
        result = callback(*args)
        if inspect.isawaitable(result):
            result = await result
        self.outputs[step_name] = result
        return result


_ACCOUNT_ID = 'closed-account'
_TIMESTAMP = '2026-01-01T00:00:00Z'
_SKILL_COMPLETED = {
    'account_id': _ACCOUNT_ID,
    'goal_id': 'goal',
    'skill_experience_id': 'experience',
    'skill_id': 'skill',
    'initial_progress': '50',
    'final_progress': '100',
    'completed_at': _TIMESTAMP,
}
_DIAGNOSTIC_COMPLETED = {
    'account_id': _ACCOUNT_ID,
    'goal_id': 'goal',
    'skill_experience_id': 'experience',
    'skill_id': 'skill',
    'initial_progress': '0',
    'completed_at': _TIMESTAMP,
    'submitted_at': _TIMESTAMP,
    'time_zone': 'UTC',
}
_COMPETENCY_MASTERED = {
    'account_id': _ACCOUNT_ID,
    'goal_id': 'goal',
    'skill_experience_id': 'experience',
    'skill_id': 'skill',
    'competency_id': 'competency',
    'progress': '100',
    'mastered_at': _TIMESTAMP,
}
_ACTIVITY_EVALUATED = {
    'account_id': _ACCOUNT_ID,
    'goal_id': 'goal',
    'skill_experience_id': 'experience',
    'skill_id': 'skill',
    'competency_id': 'competency',
    'activity_id': 'activity',
    'attempt_id': 'attempt',
    'evaluation_id': 'evaluation',
    'kind': 'learning',
    'difficulty': 'easy',
    'score': '80',
    'evaluated_at': _TIMESTAMP,
    'submitted_at': _TIMESTAMP,
    'time_zone': 'UTC',
}

_HANDLERS: tuple[tuple[str, Callable[..., Any], Mapping[str, object]], ...] = (
    (
        'skill-completed',
        RecognizeSkillCompletedJob.handle,
        _SKILL_COMPLETED,
    ),
    (
        'diagnostic-completed',
        RecognizeDiagnosticCompletedJob.handle,
        _DIAGNOSTIC_COMPLETED,
    ),
    (
        'competency-mastered',
        RecognizeCompetencyMasteredJob.handle,
        _COMPETENCY_MASTERED,
    ),
    (
        'practice-day-diagnostic',
        RecognizePracticeDayOnDiagnosticCompletedJob.handle,
        _DIAGNOSTIC_COMPLETED,
    ),
    (
        'practice-day-activity',
        RecognizePracticeDayOnActivityEvaluatedJob.handle,
        _ACTIVITY_EVALUATED,
    ),
    (
        'activity-xp',
        RecognizeActivityXpOnActivityEvaluatedJob.handle,
        _ACTIVITY_EVALUATED,
    ),
)


@pytest.mark.parametrize(
    ('job_name', 'handle_job', 'event_data'),
    _HANDLERS,
    ids=[item[0] for item in _HANDLERS],
)
def test_should_skip_event_effect_when_account_is_closed(
    job_name: str,
    handle_job: Callable[..., Any],
    event_data: Mapping[str, object],
) -> None:
    del job_name
    account_activity_provider = Mock(spec=AccountActivityProvider)
    account_activity_provider.async_activity.return_value = _DeniedActivityScope()
    use_case = Mock()
    telemetry_provider = Mock(spec=TelemetryProvider)
    if handle_job is RecognizeActivityXpOnActivityEvaluatedJob.handle:
        handler = handle_job(
            _RegistrationFake(),
            use_case,
            Mock(),
            account_activity_provider,
        )
    else:
        handler = handle_job(
            _RegistrationFake(),
            use_case,
            Mock(),
            account_activity_provider,
            telemetry_provider=telemetry_provider,
        )
    context = SimpleNamespace(
        attempt=0,
        run_id='run-id',
        event=SimpleNamespace(id='event-id', data=event_data),
        step=_StepRunner(),
    )

    asyncio.run(handler(context))

    account_activity_provider.async_activity.assert_called_once_with(_ACCOUNT_ID)
    use_case.execute.assert_not_called()
    normalized = context.step.outputs['normalize_payload']
    assert isinstance(normalized, dict)
    assert 'account_id' not in normalized


def test_should_skip_late_profile_creation_and_keep_step_output_pii_free() -> None:
    activity_provider = Mock(spec=AccountActivityProvider)
    activity_provider.async_activity.return_value = _DeniedActivityScope()
    use_case = Mock()
    handler = cast(
        'Callable[..., Any]',
        CreateProfileOnAccountActivatedJob.handle(
            cast('Inngest', _RegistrationFake()),
            use_case,
            Mock(),
            activity_provider,
            telemetry_provider=Mock(spec=TelemetryProvider),
        ),
    )
    context = SimpleNamespace(
        attempt=0,
        run_id='run-id',
        event=SimpleNamespace(
            id='event-id',
            data={
                'account_id': _ACCOUNT_ID,
                'activated_at': _TIMESTAMP,
            },
        ),
        step=_StepRunner(),
    )

    asyncio.run(handler(context))

    activity_provider.async_activity.assert_called_once_with(_ACCOUNT_ID)
    use_case.execute.assert_not_called()
    assert context.step.outputs['normalize_payload'] is None

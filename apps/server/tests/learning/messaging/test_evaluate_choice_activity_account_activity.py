from __future__ import annotations

import asyncio
from contextlib import contextmanager
import inspect
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import Mock

import pytest  # noqa: TC002 - pytest.raises is needed at runtime.

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine, Generator, Iterator

from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
)
from shifu.learning.core.use_cases import EvaluateChoiceActivityUseCase
from shifu.learning.messaging.inngest.jobs.evaluate_choice_activity_job import (
    EvaluateChoiceActivityJob,
    EvaluationJobPayload,
)
from shifu.shared.core.domain.errors import AuthorizationError

if TYPE_CHECKING:
    from shifu.shared.core.interfaces.account_activity_provider import (
        AccountActivityProvider,
    )
    from shifu.shared.core.interfaces.clock_provider import ClockProvider
    from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
    from shifu.learning.core.interfaces import LearningDatabase
    from inngest import Inngest

_PAYLOAD: EvaluationJobPayload = {
    'attempt_id': 'attempt-1',
    'run_id': 'run-1',
    'skill_experience_id': 'experience-1',
    'activity_id': 'activity-1',
    'kind': 'learning',
    'requested_at': '2026-11-21T12:00:00+00:00',
}


class _FakeInngest:
    def create_function(
        self, **_options: object
    ) -> Callable[[Callable[..., object]], Callable[..., object]]:
        return lambda handler: handler


class _FakeStep:
    async def run(
        self,
        _name: str,
        function: Callable[..., object],
        *args: object,
    ) -> object:
        result = function(*args)
        if inspect.isawaitable(result):
            return await cast('Awaitable[object]', result)
        return result


async def _run_in_thread_immediately[T](
    function: Callable[..., T],
    *args: object,
    **kwargs: object,
) -> T:
    return function(*args, **kwargs)


def _learning_database(
    account_ids: Iterator[str | None],
) -> tuple[LearningDatabase, dict[str, bool]]:
    gate_state = {'entered': False}
    attempt = SimpleNamespace(
        id='attempt-1',
        skill_experience_id='experience-1',
        activity_id='activity-1',
        kind=ActivityAttemptKind.LEARNING,
    )
    experience = SimpleNamespace(id='experience-1', goal_id='goal-1')
    evaluation = SimpleNamespace(
        status=ActivityEvaluationStatus.PENDING,
        run_id='run-1',
    )

    def find_attempt(attempt_id: str) -> SimpleNamespace:
        assert attempt_id == 'attempt-1'
        return attempt

    def find_experience(experience_id: str) -> SimpleNamespace:
        assert experience_id == 'experience-1'
        return experience

    goal_lookup_count = 0

    def find_goal(goal_id: str) -> SimpleNamespace | None:
        nonlocal goal_lookup_count
        assert goal_id == 'goal-1'
        goal_lookup_count += 1
        if goal_lookup_count == 2:
            assert gate_state['entered']
        account_id = next(account_ids)
        return SimpleNamespace(account_id=account_id) if account_id else None

    def find_evaluation(_attempt_id: str) -> SimpleNamespace:
        return evaluation

    repositories = SimpleNamespace(
        activity_attempts=SimpleNamespace(find_by_id=find_attempt),
        skill_experiences=SimpleNamespace(find_by_id=find_experience),
        goals=SimpleNamespace(find_by_id=find_goal),
        activity_evaluations=SimpleNamespace(find_by_attempt_id=find_evaluation),
    )

    @contextmanager
    def transaction() -> Generator[SimpleNamespace]:
        yield repositories

    database = SimpleNamespace(transaction=transaction)
    return cast('LearningDatabase', database), gate_state


def _job_handler(
    database: LearningDatabase,
    account_activity_provider: AccountActivityProvider,
) -> Callable[[Any], Awaitable[None]]:
    return cast(
        'Callable[[Any], Awaitable[None]]',
        EvaluateChoiceActivityJob.handle(
            cast('Inngest', _FakeInngest()),
            database,
            cast('ClockProvider', None),
            account_activity_provider=account_activity_provider,
            telemetry_provider=cast('TelemetryProvider', Mock()),
        ),
    )


async def _run_job(handler: Callable[[Any], Awaitable[None]]) -> None:
    context = SimpleNamespace(
        event=SimpleNamespace(data=_PAYLOAD, id='event-1'),
        run_id='job-run',
        attempt=0,
        step=_FakeStep(),
    )
    await handler(context)


def _drive(awaitable: Coroutine[Any, Any, None]) -> None:
    try:
        awaitable.send(None)
    except StopIteration:
        return
    finally:
        awaitable.close()
    raise AssertionError('The fake Inngest handler unexpectedly suspended.')


def test_job_revalidates_the_attempt_owner_inside_the_account_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(asyncio, 'to_thread', _run_in_thread_immediately)
    database, gate_state = _learning_database(iter(['account-1', 'account-1']))
    activity_accounts: list[str] = []

    @contextmanager
    def activity(account_id: str) -> Generator[None]:
        activity_accounts.append(account_id)
        gate_state['entered'] = True
        try:
            yield
        finally:
            gate_state['entered'] = False

    evaluated: list[str] = []

    def evaluate(
        _use_case: EvaluateChoiceActivityUseCase,
        attempt_id: str,
        _run_id: str,
    ) -> bool:
        assert gate_state['entered']
        evaluated.append(attempt_id)
        return False

    monkeypatch.setattr(EvaluateChoiceActivityUseCase, 'execute', evaluate)
    handler = _job_handler(
        database,
        cast('AccountActivityProvider', SimpleNamespace(activity=activity)),
    )

    _drive(_run_job(handler))

    assert activity_accounts == ['account-1']
    assert evaluated == ['attempt-1']
    assert not gate_state['entered']


def test_job_skips_evaluation_if_the_attempt_owner_changes_before_the_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(asyncio, 'to_thread', _run_in_thread_immediately)
    database, gate_state = _learning_database(iter(['account-1', 'account-2']))

    @contextmanager
    def activity(_account_id: str) -> Generator[None]:
        gate_state['entered'] = True
        try:
            yield
        finally:
            gate_state['entered'] = False

    evaluated = False

    def evaluate(
        _use_case: EvaluateChoiceActivityUseCase,
        _attempt_id: str,
        _run_id: str,
    ) -> bool:
        nonlocal evaluated
        evaluated = True
        return False

    monkeypatch.setattr(EvaluateChoiceActivityUseCase, 'execute', evaluate)
    handler = _job_handler(
        database,
        cast('AccountActivityProvider', SimpleNamespace(activity=activity)),
    )

    _drive(_run_job(handler))

    assert evaluated is False
    assert not gate_state['entered']


def test_job_skips_evaluation_when_the_account_gate_rejects_a_closed_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(asyncio, 'to_thread', _run_in_thread_immediately)
    database, _ = _learning_database(iter(['account-1']))

    @contextmanager
    def inactive_activity(_account_id: str) -> Generator[None]:
        raise AuthorizationError
        yield

    evaluated = False

    def evaluate(
        _use_case: EvaluateChoiceActivityUseCase,
        _attempt_id: str,
        _run_id: str,
    ) -> bool:
        nonlocal evaluated
        evaluated = True
        return False

    monkeypatch.setattr(EvaluateChoiceActivityUseCase, 'execute', evaluate)
    handler = _job_handler(
        database,
        cast('AccountActivityProvider', SimpleNamespace(activity=inactive_activity)),
    )

    _drive(_run_job(handler))

    assert evaluated is False

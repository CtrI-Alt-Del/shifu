"""The real-model eval runs a case again after a passing provider failure, waits
longer each time, never retries a rejected answer, and reports only the kind of
a failed call: class names and the HTTP status, never the error text."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from agno.agent import Agent
from agno.eval.suite import Case
from agno.exceptions import ModelProviderError
from agno.scorer.base import Score, Scorer
import pytest

from evals.eval import Eval

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from agno.models.response import ModelResponse

PRIVATE_TEXT = 'private-prompt-and-api-key-sk-secret'


class _AcceptingScorer(Scorer):
    async def ascore(self, run: Any, expected: Any = None) -> Score:
        del run, expected
        return Score(value=1, passed=True, reason='accepted')


class _RejectingScorer(Scorer):
    async def ascore(self, run: Any, expected: Any = None) -> Score:
        del run, expected
        return Score(value=0, passed=False, reason='rejected')


class _FlakyModel(Eval.SyntheticModel):
    """Fails its first calls with the given errors, then answers."""

    def __init__(self, failures: list[Exception]) -> None:
        super().__init__(lambda _text, _format: {'answer': 'ok'}, profile='flaky')
        self.failures = failures
        self.calls = 0

    async def ainvoke_stream(
        self, *args: Any, **kwargs: Any
    ) -> AsyncIterator[ModelResponse]:
        self.calls += 1
        if self.calls <= len(self.failures):
            raise self.failures[self.calls - 1]
        async for chunk in super().ainvoke_stream(*args, **kwargs):
            yield chunk


class _FlakyEval(Eval):
    selector = 'flaky'
    workflow_id = 'flaky'
    prompt_revision = 'test'

    def __init__(self, model: _FlakyModel, scorer: Scorer) -> None:
        super().__init__(mode='real')
        self.agent = Agent(name='flaky-agent', model=model, retries=0)
        self.scorer = scorer

    def cases(self) -> tuple[Case, ...]:
        return (
            Case(
                name='flaky_case',
                agent=self.agent,
                input=PRIVATE_TEXT,
                scorer=self.scorer,
            ),
        )


def _provider_error(status_code: int, *, cause: Exception | None = None) -> Exception:
    error = ModelProviderError(PRIVATE_TEXT, status_code=status_code)
    error.__cause__ = cause
    return error


def _run(
    model: _FlakyModel, scorer: Scorer | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    evaluator = _FlakyEval(model, scorer or _AcceptingScorer())
    report = evaluator.run(evaluator.cases())
    assert PRIVATE_TEXT not in json.dumps(report)
    return report, report['cases'][0]


@pytest.fixture(autouse=True)
def no_retry_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Eval, 'RETRY_BASE_DELAY_SECONDS', 0.0)


def test_a_case_passes_after_rate_limit_failures() -> None:
    model = _FlakyModel([_provider_error(429), _provider_error(429)])

    report, case = _run(model)

    assert report['status'] == 'passed'
    assert model.calls == 3
    assert case['outcome'] == 'passed'
    assert case['attempts'] == 3
    assert [error['status_code'] for error in case['retried_errors']] == [429, 429]
    assert 'error' not in case


def test_a_case_fails_with_the_last_error_when_every_attempt_fails() -> None:
    model = _FlakyModel([_provider_error(503) for _ in range(10)])

    report, case = _run(model)

    assert report['status'] == 'failed'
    assert model.calls == Eval.MAX_CASE_ATTEMPTS
    assert case['failure_code'] == 'case_error'
    assert case['attempts'] == Eval.MAX_CASE_ATTEMPTS
    assert case['error'] == {'type': 'ModelProviderError', 'status_code': 503}
    assert len(case['retried_errors']) == Eval.MAX_CASE_ATTEMPTS - 1


def test_a_failed_call_keeps_its_cause_class_but_not_its_text() -> None:
    cause = ConnectionError(PRIVATE_TEXT)
    model = _FlakyModel([_provider_error(502, cause=cause)])

    _report, case = _run(model)

    assert case['outcome'] == 'passed'
    assert case['retried_errors'] == [
        {
            'type': 'ModelProviderError',
            'cause_type': 'ConnectionError',
            'status_code': 502,
        }
    ]


@pytest.mark.parametrize('status_code', [400, 401, 402, 403, 404])
def test_a_permanent_provider_error_is_not_retried(status_code: int) -> None:
    model = _FlakyModel([_provider_error(status_code)])

    _report, case = _run(model)

    assert model.calls == 1
    assert case['failure_code'] == 'case_error'
    assert case['error'] == {'type': 'ModelProviderError', 'status_code': status_code}
    assert 'attempts' not in case


def test_a_rejected_answer_is_a_verdict_and_is_not_retried() -> None:
    model = _FlakyModel([])

    report, case = _run(model, _RejectingScorer())

    assert report['status'] == 'failed'
    assert model.calls == 1
    assert case['failure_code'] == 'scorer_rejected'
    assert 'attempts' not in case
    assert 'error' not in case


def test_the_wait_before_each_retry_grows(monkeypatch: pytest.MonkeyPatch) -> None:
    waits: list[float] = []

    async def record_wait(seconds: float) -> None:
        # Agno also yields with sleep(0) between cases; only real waits count.
        if seconds:
            waits.append(seconds)

    monkeypatch.setattr(Eval, 'RETRY_BASE_DELAY_SECONDS', 2.0)
    monkeypatch.setattr('evals.eval.asyncio.sleep', record_wait)
    model = _FlakyModel([_provider_error(429) for _ in range(10)])

    _run(model)

    assert waits == [2.0, 4.0, 8.0]

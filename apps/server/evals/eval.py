"""The base of every Shifu eval: cases, selection, execution, report and double."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
import json
import re
from time import monotonic, sleep
from typing import TYPE_CHECKING, Any, ClassVar

from agno.eval import Case, arun_cases
from agno.exceptions import ModelProviderError
from agno.models.base import Model
from agno.models.response import ModelResponse

from shifu.intelligence.ai.agno.agents.mentor_agent import (
    mentor_transport_failure_scope,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Iterator

    from agno.eval import CaseResult


class Eval(ABC):
    """One quality gate over one Agno agent or one local provider.

    A subclass declares `selector`, `workflow_id` and `prompt_revision`, builds its
    target in `__init__`, and returns its cases from `cases()`. An agent eval returns
    Agno `Case`s, scored by Agno. A provider eval returns `Eval.LocalCase`s and
    implements `run_case`. Both produce the same report.
    """

    selector: ClassVar[str]
    workflow_id: ClassVar[str]
    prompt_revision: ClassVar[str]
    DATASET_REVISION: ClassVar[str] = 'mentor-attachments-synthetic-2026-10-14.2'
    DEFAULT_TIMEOUT_SECONDS: ClassVar[int] = 90
    MAX_EVIDENCE_TEXT_CHARS: ClassVar[int] = 600
    MAX_EVIDENCE_ITEMS: ClassVar[int] = 12
    unavailable_failure_code: ClassVar[str] = 'eval_target_unavailable'
    # A real model call can fail for a moment: the provider answers 429, 5xx or an
    # error envelope (Agno reports it as 502), or the connection drops. Such a case
    # runs again, a few times, waiting longer each time. The scorer is never retried:
    # a rejected answer is a verdict, not a provider failure.
    MAX_CASE_ATTEMPTS: ClassVar[int] = 8
    RETRY_BASE_DELAY_SECONDS: ClassVar[float] = 2.0
    RETRY_MAX_DELAY_SECONDS: ClassVar[float] = 30.0
    RETRYABLE_STATUS_CODES: ClassVar[frozenset[int]] = frozenset(
        {408, 409, 425, 429, 500, 502, 503, 504, 529}
    )
    _ERROR_TYPE_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r'^(?:agent|team): ([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|_error)): '
    )

    @dataclass(frozen=True)
    class ProviderFailure:
        """What a failed model call shows without exposing private text.

        Only exception class names and the numeric HTTP status are kept. The error
        message can carry the prompt, the case input or credentials, so it never
        enters the report.
        """

        error_type: str
        cause_type: str | None
        status_code: int | None

        @property
        def retryable(self) -> bool:
            return (
                self.status_code is not None
                and self.status_code in Eval.RETRYABLE_STATUS_CODES
            )

        def as_report(self) -> dict[str, Any]:
            report: dict[str, Any] = {'type': self.error_type}
            if self.cause_type is not None:
                report['cause_type'] = self.cause_type
            if self.status_code is not None:
                report['status_code'] = self.status_code
            return report

    @dataclass
    class CaseRun:
        """One Agno case across its attempts: the last result and what failed before."""

        result: CaseResult
        failure: Eval.ProviderFailure | None = None
        retried_errors: list[dict[str, Any]] = field(default_factory=list)

    @dataclass(frozen=True)
    class LocalCase:
        """A case executed by the eval itself, without an Agno agent."""

        name: str
        tags: tuple[str, ...]
        input: Any
        expected: Any

    @dataclass(frozen=True)
    class CaseOutcome:
        passed: bool
        failure_code: str | None = None
        metrics: dict[str, Any] | None = None

    class SyntheticModel(Model):
        """Deterministic in-process model double used only in double mode."""

        def __init__(
            self,
            respond: Callable[[str, Any], dict[str, Any]],
            *,
            profile: str,
        ) -> None:
            super().__init__(
                id=f'shifu-synthetic-{profile}', name='Shifu Synthetic Eval'
            )
            self._respond = respond

        def invoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
            messages = kwargs.get('messages')
            if messages is None and args:
                messages = args[0]
            user_text = self._user_text(messages)
            payload = self._respond(user_text, kwargs.get('response_format'))
            return ModelResponse(
                role='assistant',
                content=json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
            )

        def invoke_stream(self, *args: Any, **kwargs: Any) -> Iterator[ModelResponse]:
            yield self.invoke(*args, **kwargs)

        async def ainvoke(self, *args: Any, **kwargs: Any) -> ModelResponse:
            return self.invoke(*args, **kwargs)

        async def ainvoke_stream(
            self, *args: Any, **kwargs: Any
        ) -> AsyncIterator[ModelResponse]:
            yield self.invoke(*args, **kwargs)

        def _parse_provider_response(
            self, response: Any, **_kwargs: Any
        ) -> ModelResponse:
            if isinstance(response, ModelResponse):
                return response
            return ModelResponse(role='assistant', content=str(response))

        def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
            return self._parse_provider_response(response)

        @staticmethod
        def _user_text(messages: Any) -> str:
            if not isinstance(messages, (list, tuple)):
                return ''
            return '\n'.join(
                content
                for message in messages
                if getattr(message, 'role', None) == 'user'
                and isinstance((content := getattr(message, 'content', None)), str)
            )

    def __init__(self, *, mode: str) -> None:
        self.mode = mode
        self.double = mode == 'double'
        self.model_profile = 'unavailable'
        self.agents: tuple[Any, ...] = ()
        self._provider_failure: Eval.ProviderFailure | None = None
        self._observed_models: set[int] = set()

    @property
    def dataset_revision(self) -> str:
        return self.DATASET_REVISION

    # --- cases ---------------------------------------------------------------

    @abstractmethod
    def cases(self) -> tuple[Any, ...]:
        """Every case of this eval: Agno `Case`s or `Eval.LocalCase`s."""

    def select(self, *, name: str | None, tag: str | None) -> tuple[Any, ...]:
        return tuple(
            case
            for case in self.cases()
            if (name is None or case.name == name) and (tag is None or tag in case.tags)
        )

    # --- execution -----------------------------------------------------------

    def run(self, selected: tuple[Any, ...]) -> dict[str, Any]:
        if selected and all(isinstance(case, Case) for case in selected):
            try:
                with mentor_transport_failure_scope() as failure:
                    runs = asyncio.run(self._run_agno_cases(selected))
                    failure.raise_if_failed()
            except Exception:  # noqa: BLE001 - exception text can include private input or credentials.
                return self.setup_failed_report(selected)
            case_reports = [self._agno_case_report(run) for run in runs]
        else:
            case_reports = self.run_local_cases(selected)
        return self._report(selected, case_reports)

    async def _run_agno_cases(self, selected: tuple[Any, ...]) -> list[Eval.CaseRun]:
        """Run every case once, then run again the ones that hit a passing provider failure.

        Each round runs on the same event loop, so the model clients stay valid.
        The wait before a round grows with the round, which gives a rate limit or a
        provider hiccup time to clear while the other cases keep their order.
        """
        for case in selected:
            self._observe_model(case.agent)
        runs: dict[int, Eval.CaseRun] = {}
        pending = list(enumerate(selected))
        for attempt in range(1, self.MAX_CASE_ATTEMPTS + 1):
            await self._run_round(pending, runs)
            pending = [
                (index, case)
                for index, case in pending
                if self._should_retry(runs[index])
            ]
            if not pending or attempt == self.MAX_CASE_ATTEMPTS:
                break
            for index, _case in pending:
                failure = runs[index].failure
                if failure is not None:
                    runs[index].retried_errors.append(failure.as_report())
            await asyncio.sleep(self._retry_delay(attempt))
        return [runs[index] for index in range(len(selected))]

    async def _run_round(
        self,
        pending: list[tuple[int, Any]],
        runs: dict[int, Eval.CaseRun],
    ) -> None:
        by_case: dict[int, Eval.ProviderFailure | None] = {}

        def on_case_start(_case: Case) -> None:
            self._provider_failure = None

        def on_case_end(case: Case, _result: CaseResult) -> None:
            by_case[id(case)] = self._provider_failure

        suite = await arun_cases(
            [case for _index, case in pending],
            default_timeout=self.DEFAULT_TIMEOUT_SECONDS,
            on_case_start=on_case_start,
            on_case_end=on_case_end,
        )
        for (index, case), result in zip(pending, suite.results, strict=True):
            previous = runs.get(index)
            runs[index] = self.CaseRun(
                result=result,
                failure=by_case.get(id(case)),
                retried_errors=previous.retried_errors if previous else [],
            )

    @staticmethod
    def _should_retry(run: Eval.CaseRun) -> bool:
        result = run.result
        return (
            not result.skipped
            and not result.timed_out
            and bool(result.error)
            and run.failure is not None
            and run.failure.retryable
        )

    def _observe_model(self, agent: Any) -> None:
        """Record the class names and status of a failed model call, never its text.

        Agno turns a provider error into an error event that keeps only the message,
        which the report must not carry. The wrapper below sees the exception itself
        before Agno does, and keeps just what `ProviderFailure` allows.
        """
        model = getattr(agent, 'model', None)
        if self.double or model is None or id(model) in self._observed_models:
            return
        self._observed_models.add(id(model))
        invoke = model.ainvoke
        invoke_stream = model.ainvoke_stream

        async def observed_invoke(*args: Any, **kwargs: Any) -> Any:
            try:
                return await invoke(*args, **kwargs)
            except Exception as error:
                self._provider_failure = self._provider_failure_of(error)
                raise

        async def observed_invoke_stream(
            *args: Any, **kwargs: Any
        ) -> AsyncIterator[Any]:
            try:
                async for chunk in invoke_stream(*args, **kwargs):
                    yield chunk
            except Exception as error:
                self._provider_failure = self._provider_failure_of(error)
                raise

        model.ainvoke = observed_invoke
        model.ainvoke_stream = observed_invoke_stream

    @staticmethod
    def _provider_failure_of(error: Exception) -> Eval.ProviderFailure:
        status_code = (
            error.status_code if isinstance(error, ModelProviderError) else None
        )
        cause = error.__cause__
        return Eval.ProviderFailure(
            error_type=type(error).__name__,
            cause_type=type(cause).__name__ if cause is not None else None,
            status_code=status_code
            if isinstance(status_code, int) and 100 <= status_code <= 599
            else None,
        )

    def run_local_cases(self, selected: tuple[Any, ...]) -> list[dict[str, Any]]:
        """Run `Eval.LocalCase`s one by one; a provider eval may override for batch work.

        A case whose model call fails with a passing provider status, such as a rate
        limit, runs again after a wait that grows each time, like an Agno case. A
        rejected answer is a verdict and is never run again.
        """
        reports: list[dict[str, Any]] = []
        for case in selected:
            started = monotonic()
            retried: list[dict[str, Any]] = []
            failure: Eval.ProviderFailure | None = None
            outcome = self.CaseOutcome(
                passed=False, failure_code=self.unavailable_failure_code
            )
            for attempt in range(1, self.MAX_CASE_ATTEMPTS + 1):
                try:
                    outcome = self.run_case(case)
                    failure = None
                    break
                except Exception as error:  # noqa: BLE001 - provider errors can contain case data.
                    outcome = self.CaseOutcome(
                        passed=False, failure_code=self.unavailable_failure_code
                    )
                    failure = self._local_provider_failure(error)
                    if (
                        failure is None
                        or not failure.retryable
                        or attempt == self.MAX_CASE_ATTEMPTS
                    ):
                        break
                    retried.append(failure.as_report())
                    sleep(self._retry_delay(attempt))
            report = self.local_case_report(
                case.name, outcome, duration=monotonic() - started
            )
            if retried:
                report['attempts'] = len(retried) + 1
                report['retried_errors'] = retried
            if failure is not None:
                report['error'] = failure.as_report()
            reports.append(report)
        return reports

    @classmethod
    def _retry_delay(cls, attempt: int) -> float:
        """The wait after a failed attempt: it doubles each time, up to a cap."""
        return min(
            cls.RETRY_BASE_DELAY_SECONDS * 2 ** (attempt - 1),
            cls.RETRY_MAX_DELAY_SECONDS,
        )

    @classmethod
    def _local_provider_failure(
        cls, error: BaseException
    ) -> Eval.ProviderFailure | None:
        """The failed model call along an error's causes, kept as class names and a status."""
        current: BaseException | None = error
        for _depth in range(8):
            if current is None:
                return None
            if isinstance(current, ModelProviderError):
                return cls._provider_failure_of(current)
            current = current.__cause__
        return None

    def run_case(self, case: Eval.LocalCase) -> Eval.CaseOutcome:
        raise NotImplementedError(f'{type(self).__name__} runs no local cases')

    def close(self) -> None:
        for agent in self.agents:
            close = getattr(agent, 'close', None)
            if not callable(close):
                close = getattr(getattr(agent, 'model', None), 'close', None)
            if callable(close):
                with suppress(Exception):
                    close()

    @staticmethod
    def require_model(agent: Any) -> None:
        """Real mode runs the agent's own resolved model, or the eval is Blocked."""
        if getattr(agent, 'model', None) is None:
            raise ServiceUnavailableError(
                f'{getattr(agent, "name", "agent")} has no configured model.'
            )

    # --- reports -------------------------------------------------------------

    def report_extras(self) -> dict[str, Any]:
        """Workflow-level fields a provider eval adds after its cases ran."""
        return {}

    def _report(
        self, selected: tuple[Any, ...], case_reports: list[dict[str, Any]]
    ) -> dict[str, Any]:
        successful = bool(case_reports) and all(
            case['outcome'] == 'passed' for case in case_reports
        )
        return {
            **self._report_header(selected),
            'status': 'passed' if successful else 'failed',
            'counts': {
                'selected': len(case_reports),
                'passed': sum(case['outcome'] == 'passed' for case in case_reports),
                'failed': sum(case['outcome'] == 'failed' for case in case_reports),
                'skipped': sum(case['outcome'] == 'skipped' for case in case_reports),
            },
            'cases': case_reports,
            **self.report_extras(),
        }

    def setup_failed_report(self, selected: tuple[Any, ...]) -> dict[str, Any]:
        return {
            **self._report_header(selected),
            'status': 'failed',
            'counts': {
                'selected': len(selected),
                'passed': 0,
                'failed': len(selected),
                'skipped': 0,
            },
            'failure_code': 'eval_setup_failed',
            'cases': [
                {
                    'case_id': case.name,
                    'outcome': 'failed',
                    'duration_seconds': 0.0,
                    'skipped': False,
                    'scorer_passed': False,
                    'failure_code': 'eval_setup_failed',
                }
                for case in selected
            ],
        }

    def _report_header(self, selected: tuple[Any, ...]) -> dict[str, Any]:
        return {
            'workflow': self.selector,
            'partial': len(selected) < len(self.cases()),
            'mode': self.mode,
            'model_profile': self.model_profile,
            'dataset_revision': self.dataset_revision,
            'prompt_revision': self.prompt_revision,
            'selected_case_ids': [case.name for case in selected],
        }

    @classmethod
    def _agno_case_report(cls, run: Eval.CaseRun) -> dict[str, Any]:
        result = run.result
        if result.skipped:
            outcome, failure_code = 'skipped', 'case_skipped'
        elif result.passed:
            outcome, failure_code = 'passed', None
        else:
            outcome = 'failed'
            failure_code = (
                'case_timed_out'
                if result.timed_out
                else 'case_error'
                if result.error
                else 'scorer_rejected'
            )
        report: dict[str, Any] = {
            'case_id': result.name,
            'outcome': outcome,
            'duration_seconds': round(max(result.duration_seconds, 0.0), 3),
            'skipped': result.skipped,
            'scorer_passed': result.passed if not result.skipped else None,
            'failure_code': failure_code,
        }
        if run.retried_errors:
            report['attempts'] = len(run.retried_errors) + 1
            report['retried_errors'] = run.retried_errors
        if failure_code == 'case_error':
            report['error'] = cls._error_report(result, run.failure)
        if failure_code == 'scorer_rejected':
            report['evidence'] = cls._scorer_evidence(result)
        return report

    @classmethod
    def _error_report(
        cls, result: CaseResult, failure: Eval.ProviderFailure | None
    ) -> dict[str, Any]:
        """The kind of a case error: class names and a status, never its text.

        A model call that failed is described by what the observer saw. Any other
        error keeps only its leading class name or Agno error slug, when the
        message starts with one, because the rest of the message may hold private
        input or credentials.
        """
        if failure is not None:
            return failure.as_report()
        match = cls._ERROR_TYPE_PATTERN.match(result.error or '')
        return {'type': match.group(1)} if match else {'type': 'unknown'}

    @classmethod
    def _scorer_evidence(cls, result: Any) -> dict[str, Any]:
        """What a rejected case answered and why its scorer rejected it.

        Only the model output and the scorer verdict are kept, bounded in size. The
        prompt, the case input and any error text stay out: error text can carry
        private input or credentials, and a passing case needs no evidence.
        """
        content = getattr(result.response, 'content', None)
        dump = getattr(content, 'model_dump', None)
        output = dump(mode='json') if callable(dump) else content
        evidence: dict[str, Any] = {'output': cls._bounded(output)}
        score = result.score
        if score is not None:
            evidence['scorer_reason'] = score.reason
            if score.detail:
                evidence['scorer_detail'] = cls._bounded(score.detail)
        return evidence

    @classmethod
    def _bounded(cls, value: Any) -> Any:
        """Cut long text and long lists so a report stays small."""
        if isinstance(value, str):
            extra = len(value) - cls.MAX_EVIDENCE_TEXT_CHARS
            if extra <= 0:
                return value
            return f'{value[: cls.MAX_EVIDENCE_TEXT_CHARS]}…[{extra} more characters]'
        if isinstance(value, dict):
            return {str(key): cls._bounded(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            items = [cls._bounded(item) for item in value[: cls.MAX_EVIDENCE_ITEMS]]
            extra = len(value) - cls.MAX_EVIDENCE_ITEMS
            if extra > 0:
                items.append(f'…[{extra} more items]')
            return items
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return cls._bounded(str(value))

    @staticmethod
    def local_case_report(
        name: str, outcome: Eval.CaseOutcome, *, duration: float
    ) -> dict[str, Any]:
        report: dict[str, Any] = {
            'case_id': name,
            'outcome': 'passed' if outcome.passed else 'failed',
            'duration_seconds': round(max(duration, 0.0), 3),
            'skipped': False,
            'scorer_passed': outcome.passed,
            'failure_code': None if outcome.passed else outcome.failure_code,
        }
        if outcome.metrics is not None:
            report['metrics'] = outcome.metrics
        return report

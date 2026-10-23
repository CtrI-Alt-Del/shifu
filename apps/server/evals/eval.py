"""The base of every Shifu eval: cases, selection, execution, report and double."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import suppress
from dataclasses import dataclass
import json
from time import monotonic
from typing import TYPE_CHECKING, Any, ClassVar

from agno.eval import Case, run_cases
from agno.models.base import Model
from agno.models.response import ModelResponse

from shifu.intelligence.ai.agno.agents.mentor_agent import (
    mentor_transport_failure_scope,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Iterator


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
    unavailable_failure_code: ClassVar[str] = 'eval_target_unavailable'

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
                    suite = run_cases(
                        selected, default_timeout=self.DEFAULT_TIMEOUT_SECONDS
                    )
                    failure.raise_if_failed()
            except Exception:  # noqa: BLE001 - exception text can include private input or credentials.
                return self.setup_failed_report(selected)
            case_reports = [self._agno_case_report(result) for result in suite.results]
        else:
            case_reports = self.run_local_cases(selected)
        return self._report(selected, case_reports)

    def run_local_cases(self, selected: tuple[Any, ...]) -> list[dict[str, Any]]:
        """Run `Eval.LocalCase`s one by one; a provider eval may override for batch work."""
        reports: list[dict[str, Any]] = []
        for case in selected:
            started = monotonic()
            try:
                outcome = self.run_case(case)
            except Exception:  # noqa: BLE001 - provider errors can contain case data.
                outcome = self.CaseOutcome(
                    passed=False, failure_code=self.unavailable_failure_code
                )
            reports.append(
                self.local_case_report(
                    case.name, outcome, duration=monotonic() - started
                )
            )
        return reports

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

    @staticmethod
    def _agno_case_report(result: Any) -> dict[str, Any]:
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
        return {
            'case_id': result.name,
            'outcome': outcome,
            'duration_seconds': round(max(result.duration_seconds, 0.0), 3),
            'skipped': result.skipped,
            'scorer_passed': result.passed if not result.skipped else None,
            'failure_code': failure_code,
        }

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

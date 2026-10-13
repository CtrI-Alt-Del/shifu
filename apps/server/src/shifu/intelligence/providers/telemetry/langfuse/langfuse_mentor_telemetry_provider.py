from collections.abc import Generator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from math import isfinite
from time import perf_counter
from uuid import UUID, uuid4
from typing import ClassVar, Literal, Protocol

from langfuse.types import TraceContext

from shifu.intelligence.core.domain.structures.mentor_review_result import (
    MentorReviewResult,
)


_CORRELATION: ContextVar[str | None] = ContextVar(
    'mentor_telemetry_correlation', default=None
)


@contextmanager
def mentor_telemetry_correlation() -> Generator[None]:
    token = _CORRELATION.set(str(uuid4()))
    try:
        yield
    finally:
        _CORRELATION.reset(token)


class _Observation(Protocol):
    def end(self) -> object: ...


class _Client(Protocol):
    def start_span(
        self,
        *,
        name: str,
        metadata: dict[str, str | int | float],
        input: object = None,
        output: object = None,
        trace_context: TraceContext | None = None,
    ) -> _Observation: ...

    def start_generation(
        self,
        *,
        trace_context: TraceContext | None = None,
        name: str,
        model: str,
        metadata: dict[str, str | int | float],
        usage_details: dict[str, int] | None,
        cost_details: dict[str, float] | None,
    ) -> _Observation: ...


class LangfuseMentorTelemetryProvider:
    _MODELS: ClassVar[dict[str, str]] = {
        'gpt-6-luna': 'openai/gpt-6-luna',
        'openrouter-deepseek': 'deepseek/deepseek-v4.1-flash',
        'jev': 'typesafe/jev-1.13',
        'mentor-reviewer': 'openai/gpt-6-luna',
    }
    _STAGES: ClassVar[frozenset[str]] = frozenset(
        {
            'classify',
            'retrieve',
            'context',
            'route',
            'local',
            'generate',
            'review',
            'persist',
            'publish',
        }
    )
    _COUNTS: ClassVar[frozenset[str]] = frozenset(
        {'input_tokens', 'output_tokens', 'blocks', 'retries', 'cost'}
    )
    _client: _Client | None
    _capture_content: bool

    def __init__(
        self, client: _Client | None = None, *, capture_content: bool = False
    ) -> None:
        self._client = client
        self._capture_content = capture_content

    @staticmethod
    def _end_observation(observation: _Observation) -> None:
        observation.end()

    def record_answer(
        self,
        *,
        attempt_id: str,
        block_key: str,
        version: int,
        correlation_id: str,
        answer: str,
    ) -> None:
        self._record_content(
            'mentor-answer',
            attempt_id,
            block_key,
            version,
            correlation_id,
            None,
            answer,
        )

    def record_review(
        self,
        *,
        attempt_id: str,
        block_key: str,
        version: int,
        correlation_id: str,
        answer: str,
        review: MentorReviewResult,
    ) -> None:
        probabilities = dict(review.probabilities)
        feedback = dict(review.feedback)
        self._record_content(
            'mentor-review',
            attempt_id,
            block_key,
            version,
            correlation_id,
            answer,
            {
                'approved': review.approved,
                'criteria': {
                    key: {
                        'choice': choice,
                        **(
                            {'confidence': confidence} if confidence is not None else {}
                        ),
                        **(
                            {'probabilities': dict(probabilities[key])}
                            if key in probabilities
                            else {}
                        ),
                        **({'feedback': feedback[key]} if key in feedback else {}),
                    }
                    for key, choice, confidence in review.criteria
                },
            },
        )

    def _record_content(
        self,
        name: str,
        attempt_id: str,
        block_key: str,
        version: int,
        correlation_id: str,
        input: object,
        output: object,
    ) -> None:
        if not self._capture_content or self._client is None:
            return
        correlation_id = _CORRELATION.get() or correlation_id
        try:
            trace_id = UUID(correlation_id).hex
            observation = self._client.start_span(
                name=name,
                trace_context={'trace_id': trace_id},
                metadata={
                    'attempt_id': attempt_id,
                    'block_key': block_key,
                    'version': version,
                    'correlation_id': correlation_id,
                },
                input=input,
                output=output,
            )
            self._end_observation(observation)
        except Exception:  # noqa: BLE001 - Inspection is optional and must never affect the answer.
            return

    @contextmanager
    def scope(self, stage: str) -> Generator[None]:
        started = perf_counter()
        outcome: Literal['passed', 'failed'] = 'passed'
        try:
            yield
        except BaseException:
            outcome = 'failed'
            raise
        finally:
            self.emit(
                stage,
                correlation_id=_CORRELATION.get() or str(uuid4()),
                profile='local',
                duration_ms=(perf_counter() - started) * 1000,
                counts={},
                outcome=outcome,
            )

    def emit(
        self,
        stage: str,
        *,
        correlation_id: str,
        profile: str,
        duration_ms: float,
        counts: Mapping[str, int | float],
        outcome: Literal['passed', 'failed', 'abstained', 'cancelled'],
    ) -> None:
        correlation_id = _CORRELATION.get() or correlation_id
        if (
            self._client is None
            or stage not in self._STAGES
            or profile
            not in {
                'local',
                'gpt-6-luna',
                'openrouter-deepseek',
                'jev',
                'mentor-reviewer',
            }
            or not isfinite(duration_ms)
            or duration_ms < 0
        ):
            return
        try:
            UUID(correlation_id)
        except ValueError:
            return
        metadata: dict[str, str | int | float] = {
            'correlation_id': correlation_id,
            'profile': profile,
            'duration_ms': duration_ms,
            'outcome': outcome,
        }
        metadata.update(
            {
                key: value
                for key, value in counts.items()
                if key in self._COUNTS and isfinite(value) and value >= 0
            }
        )
        try:
            self._end_observation(
                self._client.start_span(name=stage, metadata=metadata)
            )
        except Exception:  # noqa: BLE001 - Optional telemetry must never affect private execution.
            return

    def record_inference(
        self,
        profile: str,
        used_tokens: int | None,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_usd: float | None,
    ) -> None:
        model = self._MODELS.get(profile)
        if self._client is None or model is None:
            return
        if used_tokens is None and cost_usd is None:
            return
        usage_details = None
        if input_tokens is not None and output_tokens is not None:
            usage_details = {
                'input': input_tokens,
                'output': output_tokens,
                'total': used_tokens
                if used_tokens is not None
                else input_tokens + output_tokens,
            }
        elif used_tokens is not None:
            usage_details = {'total': used_tokens}
        cost_details = {'total': cost_usd} if cost_usd is not None else None
        correlation_id = _CORRELATION.get() or str(uuid4())
        try:
            trace_id = UUID(correlation_id).hex
        except ValueError:
            return
        metadata: dict[str, str | int | float] = {
            'correlation_id': correlation_id,
            'profile': profile,
        }
        try:
            observation = self._client.start_generation(
                trace_context={'trace_id': trace_id},
                name='mentor-inference',
                model=model,
                metadata=metadata,
                usage_details=usage_details,
                cost_details=cost_details,
            )
            self._end_observation(observation)
        except Exception:  # noqa: BLE001 - Optional telemetry must never affect private execution.
            return

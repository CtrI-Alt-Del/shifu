"""Mentor telemetry adapter that never records private inputs or outputs."""

from collections.abc import Generator, Mapping
from contextlib import contextmanager
from time import perf_counter
from typing import Literal
from uuid import uuid4

from shifu.intelligence.core.domain.enums import MentorSummaryFailureCode
from shifu.intelligence.core.domain.structures import MentorReviewResult
from shifu.intelligence.core.interfaces import MentorTelemetryProvider
from shifu.intelligence.providers.telemetry.mentor_telemetry_correlation import (
    current_mentor_telemetry_correlation,
)
from shifu.shared.providers.langfuse_telemetry_provider import (
    LangfuseTelemetryProvider,
)


class LangfuseMentorTelemetryProvider(MentorTelemetryProvider):
    _observability: LangfuseTelemetryProvider | None

    def __init__(self, observability: LangfuseTelemetryProvider | None = None) -> None:
        self._observability = observability

    def bind(self, observability: LangfuseTelemetryProvider | None) -> None:
        self._observability = observability

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
            if self._observability is not None:
                self._observability.record(
                    stage=stage,
                    outcome=outcome,
                    duration_ms=(perf_counter() - started) * 1000,
                    correlation_id=(
                        current_mentor_telemetry_correlation() or uuid4().hex
                    ),
                    model_profile='local',
                )

    def record_inference(
        self,
        profile: str,
        used_tokens: int | None,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_usd: float | None,
    ) -> None:
        if self._observability is None:
            return
        safe_profile = (
            profile
            if profile
            in {
                'local',
                'openrouter-title',
                'jev-rubric',
                'jev-review',
                'mentor-writer',
                'mentor-reviewer',
                'mentor-attachment-vision',
                'mentor-attachment-answer',
            }
            else None
        )
        self._observability.record(
            stage='inference',
            outcome='passed',
            duration_ms=0,
            correlation_id=current_mentor_telemetry_correlation() or uuid4().hex,
            model_profile=safe_profile,
            tokens=used_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )

    def emit(
        self,
        stage: str,
        *,
        correlation_id: str,
        profile: str,
        duration_ms: float,
        counts: Mapping[str, int],
        outcome: Literal[
            'passed', 'failed', 'abstained', 'cancelled', 'ready', 'discarded'
        ],
        failure_code: MentorSummaryFailureCode | None = None,
    ) -> None:
        if self._observability is None:
            return
        correlation_id = current_mentor_telemetry_correlation() or correlation_id
        safe_profile = (
            profile
            if profile
            in {
                'local',
                'openrouter-title',
                'jev-rubric',
                'jev-review',
                'mentor-writer',
                'mentor-reviewer',
                'mentor-attachment-answer',
                'mentor-attachment-vision',
            }
            else None
        )
        self._observability.record(
            stage=stage,
            outcome=outcome,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
            model_profile=safe_profile,
            counts=dict(counts),
            failure_code=(
                failure_code.value
                if isinstance(failure_code, MentorSummaryFailureCode)
                else None
            ),
        )

    def record_answer(
        self,
        *,
        attempt_id: str,
        block_key: str,
        version: int,
        correlation_id: str,
        answer: str,
    ) -> None:
        del attempt_id, block_key, version, answer
        correlation_id = current_mentor_telemetry_correlation() or correlation_id
        if self._observability is not None:
            self._observability.record(
                stage='infer',
                outcome='passed',
                duration_ms=0,
                correlation_id=correlation_id,
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
        del attempt_id, block_key, version, answer
        correlation_id = current_mentor_telemetry_correlation() or correlation_id
        if self._observability is not None:
            self._observability.record(
                stage='review',
                outcome='passed',
                duration_ms=0,
                correlation_id=correlation_id,
                counts={'criteria': len(review.criteria)},
            )

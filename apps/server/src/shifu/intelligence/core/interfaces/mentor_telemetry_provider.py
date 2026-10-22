from collections.abc import Mapping
from contextlib import AbstractContextManager
from typing import Literal, Protocol

from shifu.intelligence.core.domain.enums import MentorSummaryFailureCode
from shifu.intelligence.core.domain.structures import MentorReviewResult


class MentorTelemetryProvider(Protocol):
    def scope(self, stage: str) -> AbstractContextManager[None]: ...

    def record_inference(
        self,
        profile: str,
        used_tokens: int | None,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_usd: float | None,
    ) -> None: ...

    def record_answer(
        self,
        *,
        attempt_id: str,
        block_key: str,
        version: int,
        correlation_id: str,
        answer: str,
    ) -> None: ...

    def record_review(
        self,
        *,
        attempt_id: str,
        block_key: str,
        version: int,
        correlation_id: str,
        answer: str,
        review: MentorReviewResult,
    ) -> None: ...

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
    ) -> None: ...

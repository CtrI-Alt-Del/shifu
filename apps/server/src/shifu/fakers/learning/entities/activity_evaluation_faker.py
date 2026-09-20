from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.learning.core.domain.entities import ActivityEvaluation
from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.domain.structures import (
    ChoiceEvaluationResult,
    EvaluationPartResult,
)
from shifu.fakers.shared.id_provider_faker import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class ActivityEvaluationFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @staticmethod
    def _fake_parts() -> tuple[EvaluationPartResult, ...]:
        return tuple(
            ChoiceEvaluationResult(
                question_key=f'question-{position}',
                score=Decimal('100'),
                is_correct=True,
                explanation='A resposta demonstra o conceito esperado.',
            )
            for position in range(1, 4)
        )

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        attempt_id: str | None = None,
        status: ActivityEvaluationStatus = ActivityEvaluationStatus.COMPLETED,
        parts: tuple[EvaluationPartResult, ...] | None = None,
        started_at: datetime | None = None,
        score: Decimal | None = None,
        failure_code: str | None = None,
        completed_at: datetime | None = None,
        effect_applied_at: datetime | None = None,
    ) -> ActivityEvaluation:
        started = started_at or cls._faker.date_time(tzinfo=UTC)
        completed = completed_at
        resolved_score = score
        resolved_parts = parts
        if status is ActivityEvaluationStatus.COMPLETED:
            completed = completed or started
            resolved_score = score if score is not None else Decimal('100')
            resolved_parts = parts if parts is not None else cls._fake_parts()
        resolved_failure_code = (
            failure_code
            if failure_code is not None
            else 'provider-unavailable'
            if status is ActivityEvaluationStatus.FAILED
            else None
        )

        return ActivityEvaluation(
            id=id or cls._id_provider.generate(),
            attempt_id=attempt_id or cls._id_provider.generate(),
            status=status,
            parts=resolved_parts or (),
            started_at=started,
            score=resolved_score,
            failure_code=resolved_failure_code,
            completed_at=completed,
            effect_applied_at=effect_applied_at,
        )

    @classmethod
    def fake_many(
        cls,
        count: int = 10,
        **overrides: object,
    ) -> list[ActivityEvaluation]:
        fake = cast('Callable[..., ActivityEvaluation]', cls.fake)
        return [fake(**overrides) for _ in range(count)]

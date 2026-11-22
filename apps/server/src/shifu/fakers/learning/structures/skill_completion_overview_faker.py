from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.learning.core.domain.enums import StartingPointCoverage
from shifu.learning.core.domain.structures import (
    CompetencyCompletionOverview,
    SkillCompletionOverview,
    SkillReviewOverview,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class SkillCompletionOverviewFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def _fake_competencies(
        cls,
        mastered_on: date,
    ) -> tuple[CompetencyCompletionOverview, ...]:
        return tuple(
            CompetencyCompletionOverview(
                competency_id=cls._id_provider.generate(),
                competency_name=f'Competência {position}',
                position=position,
                initial_progress=Decimal('45'),
                initial_coverage=StartingPointCoverage.COMPLETE,
                final_progress=Decimal('90'),
                mastered_on=mastered_on,
            )
            for position in (1, 2)
        )

    @classmethod
    def fake(
        cls,
        *,
        started_on: date | None = None,
        completed_on: date | None = None,
        duration_days: int | None = None,
        completed_by_diagnosis: bool = False,
        learning_activity_count: int | None = None,
        learning_attempt_count: int | None = None,
        initial_result: Decimal | None = Decimal('45'),
        initial_result_coverage: StartingPointCoverage = StartingPointCoverage.COMPLETE,
        final_result: Decimal = Decimal('90'),
        competencies: tuple[CompetencyCompletionOverview, ...] | None = None,
        review: SkillReviewOverview | None = None,
    ) -> SkillCompletionOverview:
        started = started_on or date(2026, 9, 2)
        completed = completed_on or date(2026, 9, 13)
        return SkillCompletionOverview(
            started_on=started,
            completed_on=completed,
            duration_days=(
                duration_days
                if duration_days is not None
                else (completed - started).days
            ),
            completed_by_diagnosis=completed_by_diagnosis,
            learning_activity_count=(
                None
                if completed_by_diagnosis
                else learning_activity_count
                if learning_activity_count is not None
                else 3
            ),
            learning_attempt_count=(
                None
                if completed_by_diagnosis
                else learning_attempt_count
                if learning_attempt_count is not None
                else 5
            ),
            initial_result=initial_result,
            initial_result_coverage=initial_result_coverage,
            final_result=final_result,
            competencies=(
                competencies
                if competencies is not None
                else cls._fake_competencies(completed)
            ),
            review=review or SkillReviewOverview(attempt_count=0, latest_score=None),
        )

    @classmethod
    def fake_many(
        cls,
        count: int = 10,
        **overrides: object,
    ) -> list[SkillCompletionOverview]:
        fake = cast('Callable[..., SkillCompletionOverview]', cls.fake)
        return [fake(**overrides) for _ in range(count)]

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.learning.core.domain.structures import (
    CompetencyCompletionSummary,
    SkillCompletionSummary,
)
from shifu.shared.core.interfaces.fakers import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class SkillCompletionSummaryFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def _fake_competencies(cls) -> tuple[CompetencyCompletionSummary, ...]:
        return tuple(
            CompetencyCompletionSummary(
                competency_id=cls._id_provider.generate(),
                initial_progress=Decimal('45'),
                final_progress=Decimal('90'),
            )
            for _ in range(3)
        )

    @classmethod
    def fake(
        cls,
        *,
        competencies: tuple[CompetencyCompletionSummary, ...] | None = None,
        initial_progress: Decimal = Decimal('45'),
        final_progress: Decimal = Decimal('90'),
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> SkillCompletionSummary:
        started = started_at or cls._faker.date_time(tzinfo=UTC)
        return SkillCompletionSummary(
            competencies=(
                competencies if competencies is not None else cls._fake_competencies()
            ),
            initial_progress=initial_progress,
            final_progress=final_progress,
            started_at=started,
            completed_at=completed_at or started,
        )

    @classmethod
    def fake_many(
        cls,
        count: int = 10,
        **overrides: object,
    ) -> list[SkillCompletionSummary]:
        fake = cast('Callable[..., SkillCompletionSummary]', cls.fake)
        return [fake(**overrides) for _ in range(count)]

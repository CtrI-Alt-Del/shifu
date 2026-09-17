from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.learning.core.domain.entities import SkillExperience
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.structures import (
    CompetencyCompletionSummary,
    SkillCompletionSummary,
)
from shifu.fakers.shared.id_provider_faker import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class SkillExperienceFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def _fake_completion_summary(
        cls,
        *,
        started_at: datetime,
        completed_at: datetime,
    ) -> SkillCompletionSummary:
        return SkillCompletionSummary(
            competencies=(
                CompetencyCompletionSummary(
                    competency_id=cls._id_provider.generate(),
                    initial_progress=Decimal('45'),
                    final_progress=Decimal('90'),
                ),
            ),
            initial_progress=Decimal('45'),
            final_progress=Decimal('90'),
            started_at=started_at,
            completed_at=completed_at,
        )

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        goal_id: str | None = None,
        skill_id: str | None = None,
        inclusion_reason: str | None = None,
        status: SkillExperienceStatus = SkillExperienceStatus.NOT_STARTED,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        completion_summary: SkillCompletionSummary | None = None,
    ) -> SkillExperience:
        created = created_at or cls._faker.date_time(tzinfo=UTC)
        started = started_at
        completed = completed_at
        summary = completion_summary

        if status is not SkillExperienceStatus.NOT_STARTED:
            started = started or created
        if status is SkillExperienceStatus.COMPLETED:
            completed = completed or updated_at or started or created
            summary = summary or cls._fake_completion_summary(
                started_at=started or created,
                completed_at=completed,
            )

        return SkillExperience(
            id=id or cls._id_provider.generate(),
            goal_id=goal_id or cls._id_provider.generate(),
            skill_id=skill_id or cls._id_provider.generate(),
            inclusion_reason=inclusion_reason,
            status=status,
            created_at=created,
            updated_at=updated_at or completed or started or created,
            started_at=started,
            completed_at=completed,
            completion_summary=summary,
        )

    @classmethod
    def fake_many(
        cls,
        count: int = 10,
        **overrides: object,
    ) -> list[SkillExperience]:
        fake = cast('Callable[..., SkillExperience]', cls.fake)
        return [fake(**overrides) for _ in range(count)]

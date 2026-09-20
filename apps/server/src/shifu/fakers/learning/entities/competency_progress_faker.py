from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.learning.core.domain.entities import CompetencyProgress
from shifu.learning.core.domain.enums import CompetencyProgressStatus
from shifu.fakers.shared.id_provider_faker import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class CompetencyProgressFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        skill_experience_id: str | None = None,
        competency_id: str | None = None,
        content_released: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        initial_progress: Decimal | None = None,
        current_progress: Decimal | None = None,
        status: CompetencyProgressStatus | None = None,
        mastered_at: datetime | None = None,
        hard_activity_score: Decimal | None = None,
    ) -> CompetencyProgress:
        created = created_at or cls._faker.date_time(tzinfo=UTC)
        initial = initial_progress if initial_progress is not None else Decimal('35')
        current = current_progress if current_progress is not None else initial
        progress_status = status or CompetencyProgressStatus.LEARNING
        mastered = mastered_at
        if progress_status is CompetencyProgressStatus.MASTERED:
            initial = (
                initial_progress if initial_progress is not None else Decimal('90')
            )
            current = (
                current_progress if current_progress is not None else Decimal('90')
            )
            mastered = mastered or updated_at or created
            hard_activity_score = hard_activity_score or Decimal('90')

        return CompetencyProgress(
            id=id or cls._id_provider.generate(),
            skill_experience_id=skill_experience_id or cls._id_provider.generate(),
            competency_id=competency_id or cls._id_provider.generate(),
            content_released=content_released,
            created_at=created,
            updated_at=updated_at or mastered or created,
            initial_progress=initial,
            current_progress=current,
            status=progress_status,
            mastered_at=mastered,
            hard_activity_score=hard_activity_score,
        )

    @classmethod
    def fake_many(
        cls,
        count: int = 10,
        **overrides: object,
    ) -> list[CompetencyProgress]:
        fake = cast('Callable[..., CompetencyProgress]', cls.fake)
        return [fake(**overrides) for _ in range(count)]

from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.learning.core.domain.enums import (
    ActivityDifficulty,
    ActivityRecommendationType,
)
from shifu.learning.core.domain.structures import ActivityRecommendation
from shifu.fakers.shared.id_provider_faker import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class ActivityRecommendationFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        competency_id: str | None = None,
        activity_id: str | None = None,
        difficulty: ActivityDifficulty = ActivityDifficulty.EASY,
        type: ActivityRecommendationType = ActivityRecommendationType.NEW_ACTIVITY,
    ) -> ActivityRecommendation:
        return ActivityRecommendation(
            competency_id=competency_id or cls._id_provider.generate(),
            activity_id=activity_id or cls._id_provider.generate(),
            difficulty=difficulty,
            type=type,
        )

    @classmethod
    def fake_many(
        cls,
        count: int = 10,
        **overrides: object,
    ) -> list[ActivityRecommendation]:
        fake = cast('Callable[..., ActivityRecommendation]', cls.fake)
        return [fake(**overrides) for _ in range(count)]

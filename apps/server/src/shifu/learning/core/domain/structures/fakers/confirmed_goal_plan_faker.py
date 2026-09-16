from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.learning.core.domain.structures import ConfirmedGoalPlan, PlannedSkill
from shifu.shared.core.interfaces.fakers import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class ConfirmedGoalPlanFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def _fake_skills(cls) -> tuple[PlannedSkill, ...]:
        return tuple(
            PlannedSkill(
                skill_id=cls._id_provider.generate(),
                inclusion_reason=cls._faker.sentence(),
            )
            for _ in range(3)
        )

    @classmethod
    def fake(
        cls,
        *,
        title: str | None = None,
        description: str | None = None,
        skills: tuple[PlannedSkill, ...] | None = None,
    ) -> ConfirmedGoalPlan:
        return ConfirmedGoalPlan(
            title=title or cls._faker.sentence(nb_words=5).rstrip('.'),
            description=description or cls._faker.paragraph(),
            skills=skills if skills is not None else cls._fake_skills(),
        )

    @classmethod
    def fake_many(
        cls,
        count: int = 10,
        **overrides: object,
    ) -> list[ConfirmedGoalPlan]:
        fake = cast('Callable[..., ConfirmedGoalPlan]', cls.fake)
        return [fake(**overrides) for _ in range(count)]

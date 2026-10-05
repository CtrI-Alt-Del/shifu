from typing import ClassVar

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.gamification.core.domain.entities.achievement import Achievement
from shifu.gamification.core.domain.enums.achievement_criterion_kind import (
    AchievementCriterionKind,
)
from shifu.gamification.core.domain.enums.achievement_family import AchievementFamily
from shifu.gamification.core.domain.structures.achievement_criterion import (
    AchievementCriterion,
)


class AchievementFaker:
    _id_provider: ClassVar[IdProviderFaker] = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        name: str = 'Primeiro Passo',
        description: str = 'Concluir o diagnóstico de uma Habilidade.',
        family: AchievementFamily = AchievementFamily.DIAGNOSIS,
        criterion: AchievementCriterion | None = None,
        xp_reward: int = 25,
        is_active: bool = True,
    ) -> Achievement:
        kind_by_family = {
            AchievementFamily.DIAGNOSIS: AchievementCriterionKind.DIAGNOSTICS_COMPLETED,
            AchievementFamily.MASTERY: AchievementCriterionKind.COMPETENCIES_MASTERED,
            AchievementFamily.COMPLETION: AchievementCriterionKind.SKILLS_COMPLETED,
            AchievementFamily.STREAK: AchievementCriterionKind.LONGEST_STREAK,
            AchievementFamily.LEVEL: AchievementCriterionKind.LEVEL,
        }
        return Achievement.create(
            id=id if id is not None else cls._id_provider.generate(),
            name=name,
            description=description,
            family=family,
            criterion=criterion
            if criterion is not None
            else AchievementCriterion.create(kind=kind_by_family[family], target=1),
            xp_reward=xp_reward,
            is_active=is_active,
        )

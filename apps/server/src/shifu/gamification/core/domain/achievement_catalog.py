from shifu.gamification.core.domain.entities.achievement import Achievement
from shifu.gamification.core.domain.enums.achievement_criterion_kind import (
    AchievementCriterionKind,
)
from shifu.gamification.core.domain.enums.achievement_family import AchievementFamily
from shifu.gamification.core.domain.structures.achievement_criterion import (
    AchievementCriterion,
)

ACHIEVEMENT_CATALOG: tuple[Achievement, ...] = (
    Achievement.create(
        id='primeiro-passo',
        name='Primeiro Passo',
        description='Concluir o diagnóstico de uma Habilidade.',
        family=AchievementFamily.DIAGNOSIS,
        criterion=AchievementCriterion.create(
            kind=AchievementCriterionKind.DIAGNOSTICS_COMPLETED, target=1
        ),
        xp_reward=25,
    ),
    Achievement.create(
        id='explorador',
        name='Explorador',
        description='Concluir o diagnóstico de cinco Habilidades distintas.',
        family=AchievementFamily.DIAGNOSIS,
        criterion=AchievementCriterion.create(
            kind=AchievementCriterionKind.DIAGNOSTICS_COMPLETED, target=5
        ),
        xp_reward=75,
    ),
    Achievement.create(
        id='primeiro-dominio',
        name='Primeiro Domínio',
        description='Dominar uma Competência.',
        family=AchievementFamily.MASTERY,
        criterion=AchievementCriterion.create(
            kind=AchievementCriterionKind.COMPETENCIES_MASTERED, target=1
        ),
        xp_reward=25,
    ),
    Achievement.create(
        id='em-evolucao',
        name='Em Evolução',
        description='Dominar dez Competências distintas.',
        family=AchievementFamily.MASTERY,
        criterion=AchievementCriterion.create(
            kind=AchievementCriterionKind.COMPETENCIES_MASTERED, target=10
        ),
        xp_reward=100,
    ),
    Achievement.create(
        id='primeira-jornada',
        name='Primeira Jornada',
        description='Concluir uma Habilidade.',
        family=AchievementFamily.COMPLETION,
        criterion=AchievementCriterion.create(
            kind=AchievementCriterionKind.SKILLS_COMPLETED, target=1
        ),
        xp_reward=50,
    ),
    Achievement.create(
        id='colecionador-de-habilidades',
        name='Colecionador de Habilidades',
        description='Concluir cinco Habilidades distintas.',
        family=AchievementFamily.COMPLETION,
        criterion=AchievementCriterion.create(
            kind=AchievementCriterionKind.SKILLS_COMPLETED, target=5
        ),
        xp_reward=150,
    ),
    Achievement.create(
        id='consistencia-i',
        name='Consistência I',
        description='Praticar por três dias consecutivos.',
        family=AchievementFamily.STREAK,
        criterion=AchievementCriterion.create(
            kind=AchievementCriterionKind.LONGEST_STREAK, target=3
        ),
        xp_reward=25,
    ),
    Achievement.create(
        id='consistencia-ii',
        name='Consistência II',
        description='Praticar por sete dias consecutivos.',
        family=AchievementFamily.STREAK,
        criterion=AchievementCriterion.create(
            kind=AchievementCriterionKind.LONGEST_STREAK, target=7
        ),
        xp_reward=50,
    ),
    Achievement.create(
        id='consistencia-iii',
        name='Consistência III',
        description='Praticar por trinta dias consecutivos.',
        family=AchievementFamily.STREAK,
        criterion=AchievementCriterion.create(
            kind=AchievementCriterionKind.LONGEST_STREAK, target=30
        ),
        xp_reward=150,
    ),
    Achievement.create(
        id='ascendente-i',
        name='Ascendente I',
        description='Alcançar o nível 5.',
        family=AchievementFamily.LEVEL,
        criterion=AchievementCriterion.create(
            kind=AchievementCriterionKind.LEVEL, target=5
        ),
        xp_reward=50,
    ),
    Achievement.create(
        id='ascendente-ii',
        name='Ascendente II',
        description='Alcançar o nível 10.',
        family=AchievementFamily.LEVEL,
        criterion=AchievementCriterion.create(
            kind=AchievementCriterionKind.LEVEL, target=10
        ),
        xp_reward=100,
    ),
    Achievement.create(
        id='ascendente-iii',
        name='Ascendente III',
        description='Alcançar o nível 20.',
        family=AchievementFamily.LEVEL,
        criterion=AchievementCriterion.create(
            kind=AchievementCriterionKind.LEVEL, target=20
        ),
        xp_reward=250,
    ),
)

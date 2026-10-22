import pytest

from shifu.gamification.core.domain.achievement_criterion_label import (
    achievement_criterion_label,
)
from shifu.gamification.core.domain.enums import AchievementCriterionKind


@pytest.mark.parametrize(
    ('kind', 'target', 'expected'),
    [
        (
            AchievementCriterionKind.DIAGNOSTICS_COMPLETED,
            1,
            '1 diagnóstico concluído',
        ),
        (
            AchievementCriterionKind.DIAGNOSTICS_COMPLETED,
            5,
            '5 diagnósticos concluídos',
        ),
        (
            AchievementCriterionKind.COMPETENCIES_MASTERED,
            1,
            '1 Competência dominada',
        ),
        (
            AchievementCriterionKind.COMPETENCIES_MASTERED,
            3,
            '3 Competências dominadas',
        ),
        (
            AchievementCriterionKind.SKILLS_COMPLETED,
            1,
            '1 Habilidade concluída',
        ),
        (
            AchievementCriterionKind.SKILLS_COMPLETED,
            4,
            '4 Habilidades concluídas',
        ),
        (AchievementCriterionKind.LONGEST_STREAK, 7, '7 dias consecutivos'),
        (AchievementCriterionKind.LEVEL, 10, 'nível 10'),
    ],
)
def test_phrases_each_criterion_kind_in_pt_br(
    kind: AchievementCriterionKind, target: int, expected: str
) -> None:
    assert achievement_criterion_label(kind, target) == expected

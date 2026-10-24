from shifu.gamification.core.domain.enums import AchievementCriterionKind


def achievement_criterion_label(kind: AchievementCriterionKind, target: int) -> str:
    """The pt-BR phrasing of one achievement criterion.

    Shared by the Achievements tab and the XP history so both surfaces name
    the same criterion identically.
    """
    if kind is AchievementCriterionKind.DIAGNOSTICS_COMPLETED:
        noun = 'diagnóstico concluído' if target == 1 else 'diagnósticos concluídos'
        return f'{target} {noun}'
    if kind is AchievementCriterionKind.COMPETENCIES_MASTERED:
        noun = 'Competência dominada' if target == 1 else 'Competências dominadas'
        return f'{target} {noun}'
    if kind is AchievementCriterionKind.SKILLS_COMPLETED:
        noun = 'Habilidade concluída' if target == 1 else 'Habilidades concluídas'
        return f'{target} {noun}'
    if kind is AchievementCriterionKind.LONGEST_STREAK:
        return f'{target} dias consecutivos'
    return f'nível {target}'

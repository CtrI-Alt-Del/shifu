from shifu.gamification.core.domain.achievement_catalog import ACHIEVEMENT_CATALOG
from shifu.gamification.core.domain.entities import Achievement, EarnedAchievement
from shifu.gamification.core.domain.enums import (
    AchievementCriterionKind,
    AchievementFamily,
    MilestoneKind,
)
from shifu.gamification.core.domain.entities import GamificationProfile
from shifu.gamification.core.domain.structures import (
    AchievementOverviewEntry,
    AchievementsOverview,
)
from shifu.gamification.core.interfaces import GamificationDatabase

_CRITERION_TO_MILESTONE: dict[AchievementCriterionKind, MilestoneKind] = {
    AchievementCriterionKind.DIAGNOSTICS_COMPLETED: MilestoneKind.DIAGNOSIS,
    AchievementCriterionKind.COMPETENCIES_MASTERED: MilestoneKind.COMPETENCY_MASTERY,
    AchievementCriterionKind.SKILLS_COMPLETED: MilestoneKind.SKILL_COMPLETION,
}

_FAMILY_BY_CRITERION: dict[AchievementCriterionKind, AchievementFamily] = {
    AchievementCriterionKind.DIAGNOSTICS_COMPLETED: AchievementFamily.DIAGNOSIS,
    AchievementCriterionKind.COMPETENCIES_MASTERED: AchievementFamily.MASTERY,
    AchievementCriterionKind.SKILLS_COMPLETED: AchievementFamily.COMPLETION,
    AchievementCriterionKind.LONGEST_STREAK: AchievementFamily.STREAK,
    AchievementCriterionKind.LEVEL: AchievementFamily.LEVEL,
}


def _criterion_label(kind: AchievementCriterionKind, target: int) -> str:
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


class ListAchievementsUseCase:
    """Return the account's level/XP summary and the merged achievement list.

    Active catalog achievements not yet earned are shown locked, with
    criterion label and numeric progress. An `EarnedAchievement` whose
    catalog entry is retired (removed or `is_active=False`) is shown
    historical, using its own snapshotted name/criterion/xp_reward rather
    than the (possibly absent) catalog entry.
    """

    def __init__(self, database: GamificationDatabase) -> None:
        self._database = database

    def execute(self, account_id: str) -> AchievementsOverview:
        with self._database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id(account_id)
            level = profile.level if profile is not None else 1
            total_xp = profile.total_xp if profile is not None else 0
            streak_longest = profile.streak.longest if profile is not None else 0
            earned = repositories.earned_achievements.find_many_by_account_id(
                account_id
            )
            counts = {
                kind: repositories.rewarded_milestones.count_by_account_id_and_kind(
                    account_id, kind
                )
                for kind in MilestoneKind
            }

        achievements = self._build_entries(earned, level, streak_longest, counts)
        return AchievementsOverview(
            level=level,
            total_xp=total_xp,
            xp_for_next_level=(
                GamificationProfile.minimum_xp_for_level(level + 1) - total_xp
            ),
            achievements=achievements,
        )

    @classmethod
    def _build_entries(
        cls,
        earned: tuple[EarnedAchievement, ...],
        level: int,
        streak_longest: int,
        counts: dict[MilestoneKind, int],
    ) -> tuple[AchievementOverviewEntry, ...]:
        earned_by_achievement_id = {item.achievement_id: item for item in earned}
        by_id = {achievement.id: achievement for achievement in ACHIEVEMENT_CATALOG}

        entries: list[AchievementOverviewEntry] = []
        for achievement in ACHIEVEMENT_CATALOG:
            if not achievement.is_active:
                continue
            earned_row = earned_by_achievement_id.get(achievement.id)
            if earned_row is not None:
                entries.append(cls._obtained_entry(achievement, earned_row))
            else:
                entries.append(
                    cls._locked_entry(achievement, level, streak_longest, counts)
                )

        for earned_row in earned:
            if earned_row.achievement_id in by_id and by_id[
                earned_row.achievement_id
            ].is_active:
                continue
            entries.append(
                cls._historical_entry(earned_row, by_id.get(earned_row.achievement_id))
            )
        return tuple(entries)

    @staticmethod
    def _obtained_entry(
        achievement: Achievement,
        earned: EarnedAchievement,
    ) -> AchievementOverviewEntry:
        return AchievementOverviewEntry(
            code=achievement.id,
            family=achievement.family,
            name=achievement.name,
            description=achievement.description,
            criterion_label=_criterion_label(
                achievement.criterion.kind, achievement.criterion.target
            ),
            xp_reward=achievement.xp_reward,
            state='obtained',
            unlocked_at=earned.achieved_at,
            progress_current=None,
            progress_target=None,
        )

    @classmethod
    def _locked_entry(
        cls,
        achievement: Achievement,
        level: int,
        streak_longest: int,
        counts: dict[MilestoneKind, int],
    ) -> AchievementOverviewEntry:
        progress_current, progress_target = cls._progress(
            achievement, level, streak_longest, counts
        )
        return AchievementOverviewEntry(
            code=achievement.id,
            family=achievement.family,
            name=achievement.name,
            description=achievement.description,
            criterion_label=_criterion_label(
                achievement.criterion.kind, achievement.criterion.target
            ),
            xp_reward=achievement.xp_reward,
            state='locked',
            unlocked_at=None,
            progress_current=progress_current,
            progress_target=progress_target,
        )

    @staticmethod
    def _historical_entry(
        earned: EarnedAchievement,
        catalog_entry: Achievement | None,
    ) -> AchievementOverviewEntry:
        family = _FAMILY_BY_CRITERION[earned.criterion.kind]
        description = catalog_entry.description if catalog_entry is not None else ''
        return AchievementOverviewEntry(
            code=earned.achievement_id,
            family=family,
            name=earned.achievement_name,
            description=description,
            criterion_label=_criterion_label(
                earned.criterion.kind, earned.criterion.target
            ),
            xp_reward=earned.xp_reward,
            state='historical',
            unlocked_at=earned.achieved_at,
            progress_current=None,
            progress_target=None,
        )

    @staticmethod
    def _progress(
        achievement: Achievement,
        level: int,
        streak_longest: int,
        counts: dict[MilestoneKind, int],
    ) -> tuple[int, int]:
        kind = achievement.criterion.kind
        target = achievement.criterion.target
        if kind is AchievementCriterionKind.LEVEL:
            return level, target
        if kind is AchievementCriterionKind.LONGEST_STREAK:
            return streak_longest, target
        milestone_kind = _CRITERION_TO_MILESTONE[kind]
        return counts[milestone_kind], target

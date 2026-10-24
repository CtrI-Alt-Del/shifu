from shifu.gamification.core.domain.achievement_criterion_label import (
    achievement_criterion_label,
)
from shifu.gamification.core.domain.entities import EarnedAchievement, XpGrant
from shifu.gamification.core.domain.enums import XpSource
from shifu.gamification.core.domain.structures import XpHistory, XpHistoryEntry
from shifu.gamification.core.interfaces import GamificationDatabase

_DESCRIPTOR_BY_SOURCE: dict[XpSource, str] = {
    XpSource.ACTIVITY: 'Atividade',
    XpSource.DIAGNOSIS: 'Diagnóstico concluído',
    XpSource.COMPETENCY_MASTERY: 'Primeiro domínio de Competência',
    XpSource.SKILL_COMPLETION: 'Habilidade concluída',
    XpSource.ACHIEVEMENT: 'Conquista',
}


class GetXpHistoryUseCase:
    """Project the account's XP grants into a readable, ordered ledger.

    The total is summed from the projected records rather than read from the
    profile, so what is presented is always explainable by exactly the records
    presented beside it.
    """

    def __init__(self, database: GamificationDatabase) -> None:
        self._database = database

    def execute(self, account_id: str) -> XpHistory:
        # No profile lookup: an account whose profile row has not been created
        # yet simply has no grants, so it reads the empty initial history.
        with self._database.transaction() as repositories:
            grants = repositories.xp_grants.find_many_by_account_id(account_id)
            earned = repositories.earned_achievements.find_many_by_account_id(
                account_id
            )

        earned_by_achievement_id = {item.achievement_id: item for item in earned}
        entries = tuple(
            self._entry_for(grant, earned_by_achievement_id=earned_by_achievement_id)
            for grant in grants
        )
        return XpHistory(
            total_xp=sum(entry.amount for entry in entries),
            entries=entries,
        )

    @classmethod
    def _entry_for(
        cls,
        grant: XpGrant,
        *,
        earned_by_achievement_id: dict[str, EarnedAchievement],
    ) -> XpHistoryEntry:
        return XpHistoryEntry(
            grant_id=grant.id,
            amount=grant.amount,
            source=grant.origin.source,
            title=grant.origin.label,
            detail=cls._detail_for(grant, earned_by_achievement_id),
            occurred_at=grant.occurred_at,
            granted_at=grant.granted_at,
        )

    @staticmethod
    def _detail_for(
        grant: XpGrant,
        earned_by_achievement_id: dict[str, EarnedAchievement],
    ) -> str:
        base = _DESCRIPTOR_BY_SOURCE[grant.origin.source]
        if grant.origin.source is not XpSource.ACHIEVEMENT:
            return base
        # The criterion comes from the account's own earned row, not the
        # catalogue: a retired achievement must keep the criterion it was
        # actually obtained under (RP-07).
        earned = earned_by_achievement_id.get(grant.origin.reference_id)
        if earned is None:
            return base
        criterion = achievement_criterion_label(
            earned.criterion.kind, earned.criterion.target
        )
        return f'{base} · {criterion}'

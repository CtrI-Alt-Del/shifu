from datetime import datetime
from decimal import Decimal

from shifu.gamification.core.domain.entities import (
    ActivityXpBalance,
    ActivityXpRecognition,
)
from shifu.gamification.core.domain.enums import XpSource
from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.gamification.core.domain.structures import XpOrigin
from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.gamification.core.use_cases.grant_xp_use_case import GrantXpUseCase
from shifu.shared.core.interfaces import CurriculumContentProvider, IdentifierProvider

_FALLBACK_LABEL = 'Atividade avaliada'

_MAXIMUM_XP_BY_DIFFICULTY: dict[str, int] = {
    'easy': 10,
    'medium': 20,
    'hard': 30,
}


class RecognizeActivityEvaluatedUseCase:
    """Grant the incremental Activity XP for one evaluated attempt.

    No-op without a Gamification profile for the account. Idempotent via
    `ActivityXpRecognitionsRepository.try_add`, which also records the
    zero-XP outcome: a zero-amount `XpGrant` is invalid, so a recognition
    with `granted_xp == 0` is the only place that outcome is ever recorded.
    """

    def __init__(
        self,
        database: GamificationDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        identifier_provider: IdentifierProvider,
        grant_xp_use_case: GrantXpUseCase,
    ) -> None:
        self._database = database
        self._curriculum_content_provider = curriculum_content_provider
        self._identifier_provider = identifier_provider
        self._grant_xp_use_case = grant_xp_use_case

    def execute(
        self,
        account_id: str,
        activity_id: str,
        attempt_id: str,
        goal_id: str,
        skill_experience_id: str,
        *,
        difficulty: str,
        score: Decimal,
        occurred_at: datetime,
        now: datetime,
    ) -> None:
        maximum_xp = _MAXIMUM_XP_BY_DIFFICULTY.get(difficulty)
        if maximum_xp is None:
            raise InvalidGamificationError

        with self._database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id(account_id)
            if profile is None:
                return

            balance = (
                repositories.activity_xp_balances.find_by_account_id_and_activity_id(
                    account_id, activity_id
                )
            )
            is_new_balance = balance is None
            if balance is None:
                balance = ActivityXpBalance.create(
                    id=self._identifier_provider.generate(),
                    account_id=account_id,
                    activity_id=activity_id,
                    maximum_xp=maximum_xp,
                    created_at=now,
                )

            additional = balance.additional_xp_for(score)
            grant_id = self._identifier_provider.generate()
            recognition = ActivityXpRecognition.create(
                id=self._identifier_provider.generate(),
                account_id=account_id,
                activity_id=activity_id,
                attempt_id=attempt_id,
                granted_xp=additional,
                xp_grant_id=grant_id if additional else None,
                occurred_at=occurred_at,
                recognized_at=now,
            )
            if not repositories.activity_xp_recognitions.try_add(recognition):
                return

            if additional == 0:
                if is_new_balance:
                    repositories.activity_xp_balances.add(balance)
                return

            balance.recognize_score(score, recognized_at=now)
            if is_new_balance:
                repositories.activity_xp_balances.add(balance)
            else:
                repositories.activity_xp_balances.update(balance)

            origin = XpOrigin(
                source=XpSource.ACTIVITY,
                reference_id=activity_id,
                label=self._activity_title(activity_id),
                goal_id=goal_id,
                skill_experience_id=skill_experience_id,
            )
            self._grant_xp_use_case.apply_within_transaction(
                repositories,
                account_id,
                grant_id,
                additional,
                origin,
                attempt_id,
                occurred_at=occurred_at,
                now=now,
            )

    def _activity_title(self, activity_id: str) -> str:
        """The Activity's own name, for the readable origin (RP-08).

        Resolved after the idempotency check and never allowed to decide
        whether XP is granted: an unresolvable Activity falls back to the
        generic sentence so the reward still commits.
        """
        activity = self._curriculum_content_provider.get_choice_activity(activity_id)
        if activity is None:
            return _FALLBACK_LABEL
        return activity.title

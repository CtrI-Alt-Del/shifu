from shifu.gamification.core.domain.enums import ActivityXpRewardState
from shifu.gamification.core.domain.errors import GamificationProfileNotFoundError
from shifu.gamification.core.domain.structures import ActivityXpReward
from shifu.gamification.core.interfaces import GamificationDatabase


class GetActivityXpRewardUseCase:
    """Resolve one attempt's reward state for the Activity result band.

    Side-effect free: the state and cumulative numbers are read from one
    consistent transaction snapshot, never written.
    """

    def __init__(self, database: GamificationDatabase) -> None:
        self._database = database

    def execute(
        self, account_id: str, activity_id: str, attempt_id: str
    ) -> ActivityXpReward:
        with self._database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id(account_id)
            if profile is None:
                raise GamificationProfileNotFoundError

            recognition = (
                repositories.activity_xp_recognitions.find_by_account_id_and_attempt_id(
                    account_id, attempt_id
                )
            )
            balance_activity_id = (
                recognition.activity_id if recognition is not None else activity_id
            )
            balance = (
                repositories.activity_xp_balances.find_by_account_id_and_activity_id(
                    account_id, balance_activity_id
                )
            )

            if recognition is None:
                return ActivityXpReward(
                    activity_id=activity_id,
                    attempt_id=attempt_id,
                    state=ActivityXpRewardState.PENDING,
                    additional_xp=0,
                    granted_xp=balance.granted_xp if balance is not None else 0,
                    maximum_xp=balance.maximum_xp if balance is not None else None,
                )

            state = (
                ActivityXpRewardState.GRANTED
                if recognition.granted_xp > 0
                else ActivityXpRewardState.NO_ADDITIONAL
            )
            return ActivityXpReward(
                activity_id=recognition.activity_id,
                attempt_id=attempt_id,
                state=state,
                additional_xp=recognition.granted_xp,
                granted_xp=balance.granted_xp if balance is not None else 0,
                maximum_xp=balance.maximum_xp if balance is not None else None,
            )

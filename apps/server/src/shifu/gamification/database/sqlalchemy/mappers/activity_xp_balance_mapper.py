from shifu.gamification.core.domain.entities import ActivityXpBalance
from shifu.gamification.database.sqlalchemy.models import ActivityXpBalanceModel


class ActivityXpBalanceMapper:
    @staticmethod
    def to_domain(model: ActivityXpBalanceModel) -> ActivityXpBalance:
        return ActivityXpBalance(
            id=model.id,
            account_id=model.account_id,
            activity_id=model.activity_id,
            maximum_xp=model.maximum_xp,
            granted_xp=model.granted_xp,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(balance: ActivityXpBalance) -> ActivityXpBalanceModel:
        return ActivityXpBalanceModel(
            id=balance.id,
            account_id=balance.account_id,
            activity_id=balance.activity_id,
            maximum_xp=balance.maximum_xp,
            granted_xp=balance.granted_xp,
            updated_at=balance.updated_at,
        )

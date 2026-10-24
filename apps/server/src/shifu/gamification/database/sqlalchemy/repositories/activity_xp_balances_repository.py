from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.gamification.core.domain.entities import ActivityXpBalance
from shifu.gamification.database.sqlalchemy.mappers import ActivityXpBalanceMapper
from shifu.gamification.database.sqlalchemy.models import ActivityXpBalanceModel


class SqlalchemyActivityXpBalancesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_account_id_and_activity_id(
        self, account_id: str, activity_id: str
    ) -> ActivityXpBalance | None:
        model = self._session.scalar(
            select(ActivityXpBalanceModel)
            .where(
                ActivityXpBalanceModel.account_id == account_id,
                ActivityXpBalanceModel.activity_id == activity_id,
            )
            .with_for_update()
        )
        return ActivityXpBalanceMapper.to_domain(model) if model is not None else None

    def add(self, balance: ActivityXpBalance) -> None:
        self._session.add(ActivityXpBalanceMapper.to_model(balance))

    def update(self, balance: ActivityXpBalance) -> None:
        self._session.merge(ActivityXpBalanceMapper.to_model(balance))

    def remove_many_by_account_id(self, account_id: str) -> None:
        self._session.execute(
            delete(ActivityXpBalanceModel).where(
                ActivityXpBalanceModel.account_id == account_id
            )
        )

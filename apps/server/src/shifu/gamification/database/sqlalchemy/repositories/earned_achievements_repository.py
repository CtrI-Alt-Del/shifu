from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shifu.gamification.core.domain.entities import EarnedAchievement
from shifu.gamification.database.sqlalchemy.mappers import EarnedAchievementMapper
from shifu.gamification.database.sqlalchemy.models import EarnedAchievementModel


class SqlalchemyEarnedAchievementsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_many_by_account_id(
        self,
        account_id: str,
    ) -> tuple[EarnedAchievement, ...]:
        models = self._session.scalars(
            select(EarnedAchievementModel).where(
                EarnedAchievementModel.account_id == account_id
            )
        ).all()
        return tuple(EarnedAchievementMapper.to_domain(model) for model in models)

    def try_add(self, earned: EarnedAchievement) -> bool:
        try:
            with self._session.begin_nested():
                self._session.add(EarnedAchievementMapper.to_model(earned))
                self._session.flush()
        except IntegrityError:
            return False
        return True

    def remove_many_by_account_id(self, account_id: str) -> None:
        self._session.execute(
            delete(EarnedAchievementModel).where(
                EarnedAchievementModel.account_id == account_id
            )
        )

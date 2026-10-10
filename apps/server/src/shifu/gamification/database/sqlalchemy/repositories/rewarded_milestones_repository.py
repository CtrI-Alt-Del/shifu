from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shifu.gamification.core.domain.entities import RewardedMilestone
from shifu.gamification.core.domain.enums import MilestoneKind
from shifu.gamification.database.sqlalchemy.mappers import RewardedMilestoneMapper
from shifu.gamification.database.sqlalchemy.models import RewardedMilestoneModel


class SqlalchemyRewardedMilestonesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def count_by_account_id_and_kind(
        self,
        account_id: str,
        kind: MilestoneKind,
    ) -> int:
        count = self._session.scalar(
            select(func.count())
            .select_from(RewardedMilestoneModel)
            .where(
                RewardedMilestoneModel.account_id == account_id,
                RewardedMilestoneModel.kind == kind.value,
            )
        )
        return count or 0

    def try_add(self, milestone: RewardedMilestone) -> bool:
        try:
            with self._session.begin_nested():
                self._session.add(RewardedMilestoneMapper.to_model(milestone))
                self._session.flush()
        except IntegrityError:
            return False
        return True

    def remove_many_by_account_id(self, account_id: str) -> None:
        self._session.execute(
            delete(RewardedMilestoneModel).where(
                RewardedMilestoneModel.account_id == account_id
            )
        )

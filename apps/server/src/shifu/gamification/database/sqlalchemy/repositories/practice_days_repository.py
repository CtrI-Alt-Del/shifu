from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shifu.gamification.core.domain.entities import PracticeDay
from shifu.gamification.database.sqlalchemy.mappers import PracticeDayMapper
from shifu.gamification.database.sqlalchemy.models import PracticeDayModel


class SqlalchemyPracticeDaysRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def try_add(self, practice_day: PracticeDay) -> bool:
        try:
            with self._session.begin_nested():
                self._session.add(PracticeDayMapper.to_model(practice_day))
                self._session.flush()
        except IntegrityError:
            return False
        return True

    def find_many_dates_by_account_id(self, account_id: str) -> tuple[date, ...]:
        rows = self._session.scalars(
            select(PracticeDayModel.practice_date)
            .where(PracticeDayModel.account_id == account_id)
            .order_by(PracticeDayModel.practice_date)
        )
        return tuple(rows)

    def remove_many_by_account_id(self, account_id: str) -> None:
        self._session.execute(
            delete(PracticeDayModel).where(PracticeDayModel.account_id == account_id)
        )

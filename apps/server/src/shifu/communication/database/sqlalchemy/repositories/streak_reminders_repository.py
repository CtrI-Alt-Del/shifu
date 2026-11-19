from datetime import date, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shifu.communication.core.domain.entities import StreakReminder
from shifu.communication.core.domain.enums import StreakReminderStatus
from shifu.communication.database.sqlalchemy.mappers import StreakReminderMapper
from shifu.communication.database.sqlalchemy.models import StreakReminderModel


class SqlalchemyStreakRemindersRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id_for_update(self, reminder_id: str) -> StreakReminder | None:
        model = self._session.scalar(
            select(StreakReminderModel)
            .where(StreakReminderModel.id == reminder_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return StreakReminderMapper.to_domain(model) if model is not None else None

    def find_by_account_id_and_local_date(
        self,
        account_id: str,
        local_date: date,
    ) -> StreakReminder | None:
        model = self._session.scalar(
            select(StreakReminderModel).where(
                StreakReminderModel.account_id == account_id,
                StreakReminderModel.local_date == local_date,
            )
        )
        return StreakReminderMapper.to_domain(model) if model is not None else None

    def try_add(self, reminder: StreakReminder) -> bool:
        try:
            with self._session.begin_nested():
                self._session.add(StreakReminderMapper.to_model(reminder))
                self._session.flush()
        except IntegrityError:
            return False
        return True

    def update(self, reminder: StreakReminder) -> None:
        self._session.merge(StreakReminderMapper.to_model(reminder))
        self._session.flush()

    def find_many_pending_by_account_id(
        self, account_id: str
    ) -> tuple[StreakReminder, ...]:
        models = self._session.scalars(
            select(StreakReminderModel)
            .where(
                StreakReminderModel.account_id == account_id,
                StreakReminderModel.status == StreakReminderStatus.PENDING.value,
            )
            .order_by(StreakReminderModel.local_date)
            .with_for_update()
        )
        return tuple(StreakReminderMapper.to_domain(model) for model in models)

    def remove_many_by_account_id(self, account_id: str) -> None:
        self._session.flush()
        self._session.execute(
            delete(StreakReminderModel).where(
                StreakReminderModel.account_id == account_id
            )
        )

    def find_many_open_by_account_id(
        self,
        account_id: str,
        *,
        now: datetime,
    ) -> tuple[StreakReminder, ...]:
        models = self._session.scalars(
            select(StreakReminderModel)
            .where(
                StreakReminderModel.account_id == account_id,
                StreakReminderModel.expires_at > now,
            )
            .order_by(StreakReminderModel.local_date)
            .with_for_update()
        )
        return tuple(StreakReminderMapper.to_domain(model) for model in models)

    def remove(self, reminder: StreakReminder) -> None:
        self._session.flush()
        self._session.execute(
            delete(StreakReminderModel).where(StreakReminderModel.id == reminder.id)
        )

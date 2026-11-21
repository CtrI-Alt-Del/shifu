from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shifu.communication.core.domain.entities import StreakReminderPreference
from shifu.communication.database.sqlalchemy.mappers import (
    StreakReminderPreferenceMapper,
)
from shifu.communication.database.sqlalchemy.models import (
    StreakReminderPreferenceModel,
)


class SqlalchemyStreakReminderPreferencesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_account_id(self, account_id: str) -> StreakReminderPreference | None:
        model = self._session.get(StreakReminderPreferenceModel, account_id)
        return (
            StreakReminderPreferenceMapper.to_domain(model)
            if model is not None
            else None
        )

    def add(self, preference: StreakReminderPreference) -> None:
        self._session.add(StreakReminderPreferenceMapper.to_model(preference))
        self._session.flush()

    def try_add(self, preference: StreakReminderPreference) -> bool:
        try:
            with self._session.begin_nested():
                self._session.add(StreakReminderPreferenceMapper.to_model(preference))
                self._session.flush()
        except IntegrityError:
            return False
        return True

    def update(self, preference: StreakReminderPreference) -> None:
        self._session.merge(StreakReminderPreferenceMapper.to_model(preference))
        self._session.flush()

    def remove_by_account_id(self, account_id: str) -> None:
        self._session.execute(
            delete(StreakReminderPreferenceModel).where(
                StreakReminderPreferenceModel.account_id == account_id
            )
        )

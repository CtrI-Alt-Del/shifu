from shifu.communication.core.domain.entities import StreakReminderPreference
from shifu.communication.database.sqlalchemy.models import (
    StreakReminderPreferenceModel,
)


class StreakReminderPreferenceMapper:
    @staticmethod
    def to_domain(model: StreakReminderPreferenceModel) -> StreakReminderPreference:
        return StreakReminderPreference(
            id=model.account_id,
            enabled=model.enabled,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(
        preference: StreakReminderPreference,
    ) -> StreakReminderPreferenceModel:
        return StreakReminderPreferenceModel(
            account_id=preference.id,
            enabled=preference.enabled,
            updated_at=preference.updated_at,
        )

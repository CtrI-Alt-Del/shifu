from shifu.communication.core.domain.entities import StreakReminder
from shifu.communication.core.domain.enums import StreakReminderStatus
from shifu.communication.database.sqlalchemy.models import StreakReminderModel


class StreakReminderMapper:
    @staticmethod
    def to_domain(model: StreakReminderModel) -> StreakReminder:
        return StreakReminder(
            id=model.id,
            account_id=model.account_id,
            local_date=model.local_date,
            streak_days=model.streak_days,
            status=StreakReminderStatus(model.status),
            expires_at=model.expires_at,
            attempt_count=model.attempt_count,
            next_attempt_at=model.next_attempt_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            completed_at=model.completed_at,
        )

    @staticmethod
    def to_model(reminder: StreakReminder) -> StreakReminderModel:
        return StreakReminderModel(
            id=reminder.id,
            account_id=reminder.account_id,
            local_date=reminder.local_date,
            streak_days=reminder.streak_days,
            status=reminder.status.value,
            expires_at=reminder.expires_at,
            attempt_count=reminder.attempt_count,
            next_attempt_at=reminder.next_attempt_at,
            created_at=reminder.created_at,
            updated_at=reminder.updated_at,
            completed_at=reminder.completed_at,
        )

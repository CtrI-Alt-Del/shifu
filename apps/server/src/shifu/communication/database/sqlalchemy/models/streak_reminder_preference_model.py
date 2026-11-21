from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class StreakReminderPreferenceModel(Model):
    __tablename__ = 'communication_streak_reminder_preferences'

    account_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class PushDeliveryModel(Model):
    __tablename__ = 'communication_push_deliveries'
    __table_args__ = (
        UniqueConstraint(
            'reminder_id',
            'subscription_id',
            name='uq_communication_push_deliveries_reminder_subscription',
        ),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    reminder_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('communication_streak_reminders.id', ondelete='CASCADE'),
        nullable=False,
    )
    # No foreign key: removing a gone browser keeps its delivery history until
    # the account data is purged.
    subscription_id: Mapped[str] = mapped_column(String(26), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

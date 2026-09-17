from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class DeliveryAttemptModel(Model):
    __tablename__ = 'communication_delivery_attempts'

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    communication_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('communication_messages.id', ondelete='CASCADE'),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

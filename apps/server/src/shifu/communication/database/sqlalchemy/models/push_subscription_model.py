from datetime import datetime

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class PushSubscriptionModel(Model):
    __tablename__ = 'communication_push_subscriptions'
    __table_args__ = (
        UniqueConstraint(
            'endpoint',
            name='uq_communication_push_subscriptions_endpoint',
        ),
        Index('ix_communication_push_subscriptions_account_id', 'account_id'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(2048), nullable=False)
    p256dh_key: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

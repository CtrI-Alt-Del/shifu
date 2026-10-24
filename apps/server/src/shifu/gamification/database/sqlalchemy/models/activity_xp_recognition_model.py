from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class ActivityXpRecognitionModel(Model):
    __tablename__ = 'gamification_activity_xp_recognitions'
    __table_args__ = (
        UniqueConstraint(
            'account_id',
            'attempt_id',
            name='uq_gamification_activity_xp_recognition_account_attempt',
        ),
        Index('ix_gamification_activity_xp_recognition_account_id', 'account_id'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    activity_id: Mapped[str] = mapped_column(String(26), nullable=False)
    attempt_id: Mapped[str] = mapped_column(String(26), nullable=False)
    granted_xp: Mapped[int] = mapped_column(Integer, nullable=False)
    xp_grant_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    recognized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

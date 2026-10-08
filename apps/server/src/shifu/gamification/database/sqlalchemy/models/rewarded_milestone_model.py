from datetime import datetime

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class RewardedMilestoneModel(Model):
    __tablename__ = 'gamification_rewarded_milestones'
    __table_args__ = (
        UniqueConstraint(
            'account_id',
            'kind',
            'subject_id',
            name='uq_gamification_rewarded_milestone_account_kind_subject',
        ),
        Index('ix_gamification_rewarded_milestone_account_id', 'account_id'),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), nullable=False)
    fact_id: Mapped[str] = mapped_column(String(26), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(26), nullable=False)
    xp_grant_id: Mapped[str] = mapped_column(String(26), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    rewarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

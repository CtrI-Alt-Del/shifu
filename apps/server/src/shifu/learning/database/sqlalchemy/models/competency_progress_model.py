from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.base import Base


class CompetencyProgressModel(Base):
    __tablename__ = 'learning_competency_progresses'

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    skill_experience_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('learning_skill_experiences.id', ondelete='CASCADE'),
        nullable=False,
    )
    competency_id: Mapped[str] = mapped_column(String(26), nullable=False)
    content_released: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    initial_progress: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    current_progress: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mastered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

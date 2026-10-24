from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class LearnerMemoryFenceModel(Model):
    __tablename__ = 'intelligence_learner_memory_fences'

    account_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    deleted_through: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

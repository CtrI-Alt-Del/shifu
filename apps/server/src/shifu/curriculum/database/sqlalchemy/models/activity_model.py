from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class ActivityModel(Model):
    __tablename__ = 'curriculum_activities'

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    competency_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('curriculum_competencies.id', ondelete='CASCADE'),
        nullable=False,
    )
    activity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    objective: Mapped[str] = mapped_column(String(4000), nullable=False)
    questions: Mapped[object] = mapped_column(JSON, nullable=False)
    evaluation_rule: Mapped[object] = mapped_column(JSON, nullable=False)

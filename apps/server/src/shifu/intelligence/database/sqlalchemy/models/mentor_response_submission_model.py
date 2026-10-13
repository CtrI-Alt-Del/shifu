from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from shifu.shared.database.sqlalchemy.model import Model


class MentorResponseSubmissionModel(Model):
    __tablename__ = 'intelligence_mentor_response_submissions'
    account_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    submission_key: Mapped[str] = mapped_column(String(36), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('intelligence_mentor_response_attempts.id', ondelete='CASCADE'),
        nullable=False,
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)

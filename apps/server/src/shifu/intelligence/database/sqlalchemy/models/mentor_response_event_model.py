from datetime import datetime
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    ForeignKeyConstraint,
    CheckConstraint,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from shifu.shared.database.sqlalchemy.model import Model


class MentorResponseEventModel(Model):
    __tablename__ = 'intelligence_mentor_response_events'
    __table_args__ = (
        ForeignKeyConstraint(
            ['session_id', 'attempt_id'],
            [
                'intelligence_mentor_response_attempts.session_id',
                'intelligence_mentor_response_attempts.id',
            ],
            ondelete='CASCADE',
        ),
        CheckConstraint(
            "kind IN ('status','consultation','block','completed','failed','cancelled')",
            name='ck_mentor_event_kind',
        ),
        CheckConstraint(
            "status IN ('queued','processing','completed','failed','cancelled')",
            name='ck_mentor_event_status',
        ),
        CheckConstraint(
            "progress IS NULL OR (kind = 'status' AND status = 'processing' AND progress IN ('write-answer','review-answer'))",
            name='ck_mentor_event_progress',
        ),
        CheckConstraint('sequence > 0', name='ck_mentor_event_sequence'),
        CheckConstraint(
            "consultation IS NULL OR consultation IN ('learning','curriculum','gamification')",
            name='ck_mentor_event_consultation',
        ),
        CheckConstraint(
            "(kind = 'block' AND block_key IS NOT NULL AND ordinal >= 0 AND content IS NOT NULL) OR (kind <> 'block' AND block_key IS NULL AND ordinal IS NULL AND content IS NULL)",
            name='ck_mentor_event_block_shape',
        ),
        CheckConstraint(
            "jsonb_typeof(sources) = 'array' AND (kind = 'block' OR sources = '[]'::jsonb)",
            name='ck_mentor_event_sources_shape',
        ),
        UniqueConstraint('attempt_id', 'block_key', name='uq_mentor_attempt_block'),
        Index(
            'uq_mentor_attempt_ordinal',
            'attempt_id',
            'ordinal',
            unique=True,
            postgresql_where=text("kind = 'block'"),
        ),
    )
    session_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('intelligence_mentor_sessions.id', ondelete='CASCADE'),
        primary_key=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey('intelligence_mentor_response_attempts.id', ondelete='CASCADE'),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    block_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ordinal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    sources: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    progress: Mapped[str | None] = mapped_column(String(32), nullable=True)
    consultation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

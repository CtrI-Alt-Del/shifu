from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from shifu.shared.database.sqlalchemy.model import Model


class MentorAttachmentChunkModel(Model):
    __tablename__ = 'intelligence_mentor_attachment_chunks'
    __table_args__ = (
        CheckConstraint('generation > 0', name='ck_mentor_attachment_chunk_generation'),
        CheckConstraint(
            'page_number IS NULL OR page_number > 0',
            name='ck_mentor_attachment_chunk_page',
        ),
        UniqueConstraint(
            'attachment_id',
            'generation',
            'locator',
            name='uq_mentor_attachment_chunk_locator',
        ),
        Index('ix_mentor_attachment_chunk_generation', 'attachment_id', 'generation'),
    )

    chunk_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    attachment_id: Mapped[str] = mapped_column(
        String(26),
        ForeignKey(
            'intelligence_mentor_attachments.id',
            ondelete='CASCADE',
            name='fk_mentor_attachment_chunk_attachment',
        ),
        nullable=False,
    )
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    locator: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

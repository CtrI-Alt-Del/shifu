from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.core.domain.structures import MentorAttachmentChunk
from shifu.intelligence.database.sqlalchemy.mappers import MentorAttachmentChunkMapper
from shifu.intelligence.database.sqlalchemy.models import (
    MentorAttachmentChunkModel,
    MentorAttachmentModel,
    MentorMessageModel,
    MentorSessionModel,
)


class SqlalchemyMentorAttachmentChunksRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_many(self, chunks: tuple[MentorAttachmentChunk, ...]) -> None:
        if chunks:
            self._session.add_all(
                [MentorAttachmentChunkMapper.to_model(chunk) for chunk in chunks]
            )
            self._session.flush()

    def find_by_attachment_id(
        self, attachment_id: str, generation: int
    ) -> tuple[MentorAttachmentChunk, ...]:
        models = self._session.scalars(
            select(MentorAttachmentChunkModel)
            .where(
                MentorAttachmentChunkModel.attachment_id == attachment_id,
                MentorAttachmentChunkModel.generation == generation,
            )
            .order_by(
                MentorAttachmentChunkModel.page_number,
                MentorAttachmentChunkModel.locator,
            )
        )
        return tuple(
            MentorAttachmentChunkMapper.to_structure(model) for model in models
        )

    def find_many_eligible(
        self,
        account_id: str,
        session_id: str,
        attachment_ids: tuple[str, ...],
        page_numbers: tuple[int, ...],
    ) -> tuple[MentorAttachmentChunk, ...]:
        if not attachment_ids:
            return ()
        query = (
            select(MentorAttachmentChunkModel)
            .join(
                MentorAttachmentModel,
                MentorAttachmentModel.id == MentorAttachmentChunkModel.attachment_id,
            )
            .join(
                MentorMessageModel,
                MentorMessageModel.id == MentorAttachmentModel.message_id,
            )
            .join(
                MentorSessionModel,
                MentorSessionModel.id == MentorMessageModel.session_id,
            )
            .where(
                MentorSessionModel.account_id == account_id,
                MentorSessionModel.id == session_id,
                MentorSessionModel.deleted_at.is_(None),
                MentorAttachmentModel.session_id == session_id,
                MentorAttachmentModel.account_id == account_id,
                MentorAttachmentModel.status.in_(
                    [
                        MentorAttachmentStatus.READY.value,
                        MentorAttachmentStatus.PARTIAL.value,
                    ]
                ),
                MentorAttachmentModel.id.in_(attachment_ids),
                MentorAttachmentChunkModel.generation
                == MentorAttachmentModel.generation,
            )
        )
        if page_numbers:
            query = query.where(
                MentorAttachmentChunkModel.page_number.in_(page_numbers)
            )
        models = self._session.scalars(
            query.order_by(
                MentorAttachmentModel.id,
                MentorAttachmentChunkModel.page_number,
                MentorAttachmentChunkModel.locator,
            )
        )
        return tuple(
            MentorAttachmentChunkMapper.to_structure(model) for model in models
        )

    def remove_by_attachment_id(self, attachment_id: str) -> None:
        self._session.execute(
            delete(MentorAttachmentChunkModel).where(
                MentorAttachmentChunkModel.attachment_id == attachment_id
            )
        )

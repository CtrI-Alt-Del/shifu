from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.intelligence.core.domain.entities import MentorAttachmentBatch
from shifu.intelligence.database.sqlalchemy.mappers import MentorAttachmentBatchMapper
from shifu.intelligence.database.sqlalchemy.models import (
    MentorAttachmentBatchModel,
)


class SqlalchemyMentorAttachmentBatchesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(
        self, batch_id: str, *, for_update: bool = False
    ) -> MentorAttachmentBatch | None:
        query = select(MentorAttachmentBatchModel).where(
            MentorAttachmentBatchModel.id == batch_id
        )
        if for_update:
            query = query.with_for_update()
        model = self._session.scalar(query)
        return (
            MentorAttachmentBatchMapper.to_entity(model) if model is not None else None
        )

    def add(self, batch: MentorAttachmentBatch) -> None:
        self._session.add(MentorAttachmentBatchMapper.to_model(batch))
        self._session.flush()

    def update(self, batch: MentorAttachmentBatch) -> None:
        self._session.merge(MentorAttachmentBatchMapper.to_model(batch))
        self._session.flush()

    def find_by_account_id(self, account_id: str) -> tuple[MentorAttachmentBatch, ...]:
        models = self._session.scalars(
            select(MentorAttachmentBatchModel)
            .where(MentorAttachmentBatchModel.account_id == account_id)
            .order_by(MentorAttachmentBatchModel.id)
        )
        return tuple(MentorAttachmentBatchMapper.to_entity(model) for model in models)

    def find_by_session_id(
        self, account_id: str, session_id: str
    ) -> tuple[MentorAttachmentBatch, ...]:
        models = self._session.scalars(
            select(MentorAttachmentBatchModel)
            .where(
                MentorAttachmentBatchModel.account_id == account_id,
                MentorAttachmentBatchModel.session_id == session_id,
            )
            .order_by(MentorAttachmentBatchModel.id)
        )
        return tuple(MentorAttachmentBatchMapper.to_entity(model) for model in models)

    def find_expired(
        self, now: datetime, limit: int
    ) -> tuple[MentorAttachmentBatch, ...]:
        models = self._session.scalars(
            select(MentorAttachmentBatchModel)
            .where(
                MentorAttachmentBatchModel.expires_at <= now,
                MentorAttachmentBatchModel.revoked_at.is_(None),
                MentorAttachmentBatchModel.consumed_by_message_id.is_(None),
            )
            .order_by(
                MentorAttachmentBatchModel.expires_at, MentorAttachmentBatchModel.id
            )
            .limit(limit)
        )
        return tuple(MentorAttachmentBatchMapper.to_entity(model) for model in models)

    def remove(self, batch_id: str) -> None:
        self._session.execute(
            delete(MentorAttachmentBatchModel).where(
                MentorAttachmentBatchModel.id == batch_id
            )
        )

from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from shifu.intelligence.core.domain.entities import MentorAttachment
from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.intelligence.database.sqlalchemy.mappers import MentorAttachmentMapper
from shifu.intelligence.database.sqlalchemy.models import (
    MentorAttachmentBatchModel,
    MentorAttachmentModel,
)


class SqlalchemyMentorAttachmentsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(
        self, attachment_id: str, *, for_update: bool = False
    ) -> MentorAttachment | None:
        query = select(MentorAttachmentModel).where(
            MentorAttachmentModel.id == attachment_id
        )
        if for_update:
            query = query.with_for_update()
        model = self._session.scalar(query)
        return MentorAttachmentMapper.to_entity(model) if model is not None else None

    def find_by_upload_key(
        self, batch_id: str, upload_key: str
    ) -> MentorAttachment | None:
        model = self._session.scalar(
            select(MentorAttachmentModel).where(
                MentorAttachmentModel.batch_id == batch_id,
                MentorAttachmentModel.upload_key == upload_key,
            )
        )
        return MentorAttachmentMapper.to_entity(model) if model is not None else None

    def find_by_batch_id(self, batch_id: str) -> tuple[MentorAttachment, ...]:
        models = self._session.scalars(
            select(MentorAttachmentModel)
            .where(MentorAttachmentModel.batch_id == batch_id)
            .order_by(MentorAttachmentModel.created_at, MentorAttachmentModel.id)
        )
        return tuple(MentorAttachmentMapper.to_entity(model) for model in models)

    def find_by_message_id(self, message_id: str) -> tuple[MentorAttachment, ...]:
        models = self._session.scalars(
            select(MentorAttachmentModel)
            .where(
                MentorAttachmentModel.message_id == message_id,
                MentorAttachmentModel.status != MentorAttachmentStatus.REMOVED.value,
            )
            .order_by(MentorAttachmentModel.id)
        )
        return tuple(MentorAttachmentMapper.to_entity(model) for model in models)

    def find_by_session_id(
        self, account_id: str, session_id: str
    ) -> tuple[MentorAttachment, ...]:
        models = self._session.scalars(
            select(MentorAttachmentModel)
            .outerjoin(
                MentorAttachmentBatchModel,
                MentorAttachmentBatchModel.id == MentorAttachmentModel.batch_id,
            )
            .where(
                MentorAttachmentModel.account_id == account_id,
                or_(
                    MentorAttachmentModel.session_id == session_id,
                    MentorAttachmentBatchModel.session_id == session_id,
                ),
            )
            .order_by(MentorAttachmentModel.id)
        )
        return tuple(MentorAttachmentMapper.to_entity(model) for model in models)

    def find_for_cleanup(
        self,
        account_id: str,
        session_id: str | None,
        batch_id: str | None,
        *,
        removed_only: bool = True,
    ) -> tuple[MentorAttachment, ...]:
        query = select(MentorAttachmentModel).where(
            MentorAttachmentModel.account_id == account_id
        )
        if session_id is not None:
            query = query.outerjoin(
                MentorAttachmentBatchModel,
                MentorAttachmentBatchModel.id == MentorAttachmentModel.batch_id,
            ).where(
                or_(
                    MentorAttachmentModel.session_id == session_id,
                    MentorAttachmentBatchModel.session_id == session_id,
                )
            )
        elif batch_id is not None:
            query = query.where(MentorAttachmentModel.batch_id == batch_id)
        if removed_only:
            query = query.where(
                MentorAttachmentModel.status == MentorAttachmentStatus.REMOVED.value
            )
        models = self._session.scalars(query.order_by(MentorAttachmentModel.id))
        return tuple(MentorAttachmentMapper.to_entity(model) for model in models)

    def count_active_in_batch(self, batch_id: str) -> int:
        count = self._session.scalar(
            select(func.count())
            .select_from(MentorAttachmentModel)
            .where(
                MentorAttachmentModel.batch_id == batch_id,
                MentorAttachmentModel.status != MentorAttachmentStatus.REMOVED.value,
            )
        )
        return int(count or 0)

    def add(self, attachment: MentorAttachment) -> None:
        self._session.add(MentorAttachmentMapper.to_model(attachment))
        self._session.flush()

    def update(self, attachment: MentorAttachment) -> None:
        self._session.merge(MentorAttachmentMapper.to_model(attachment))
        self._session.flush()

    def remove(self, attachment_id: str) -> None:
        model = self._session.get(MentorAttachmentModel, attachment_id)
        if model is not None:
            self._session.delete(model)
            self._session.flush()

    def find_expired_reservations(
        self, now: datetime, limit: int
    ) -> tuple[MentorAttachment, ...]:
        upload_timeout = now - timedelta(minutes=5)
        models = self._session.scalars(
            select(MentorAttachmentModel)
            .where(
                or_(
                    (
                        (
                            MentorAttachmentModel.status
                            == MentorAttachmentStatus.UPLOADING.value
                        )
                        & (MentorAttachmentModel.created_at <= upload_timeout)
                    ),
                    (
                        (
                            MentorAttachmentModel.status
                            == MentorAttachmentStatus.PROCESSING.value
                        )
                        & (MentorAttachmentModel.claim_expires_at <= now)
                    ),
                )
            )
            .order_by(MentorAttachmentModel.created_at, MentorAttachmentModel.id)
            .limit(limit)
        )
        return tuple(MentorAttachmentMapper.to_entity(model) for model in models)

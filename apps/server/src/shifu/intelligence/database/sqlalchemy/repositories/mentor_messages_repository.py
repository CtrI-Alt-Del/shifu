from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import Select

from shifu.intelligence.core.domain.entities import MentorMessage
from shifu.intelligence.core.domain.enums import (
    MentorAttachmentStatus,
    MentorMessageRole,
)
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentView,
    MentorMessagesPage,
    MentorMessageVolume,
    MentorSummaryBoundary,
)
from shifu.intelligence.database.sqlalchemy.mappers import MentorMessageMapper
from shifu.intelligence.database.sqlalchemy.models import (
    MentorAttachmentModel,
    MentorMessageModel,
    MentorSessionModel,
)
from shifu.intelligence.database.sqlalchemy.repositories.mentor_cursor import (
    MentorCursor,
)


class SqlalchemyMentorMessagesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_many(
        self, account_id: str, session_id: str, cursor: str | None
    ) -> MentorMessagesPage:
        query = (
            select(MentorMessageModel)
            .join(
                MentorSessionModel,
                MentorSessionModel.id == MentorMessageModel.session_id,
            )
            .where(
                MentorSessionModel.account_id == account_id,
                MentorSessionModel.id == session_id,
                MentorSessionModel.deleted_at.is_(None),
            )
        )
        if cursor is not None:
            payload = MentorCursor.decode(cursor)
            if (
                payload.get('kind') != 'messages'
                or payload.get('account_id') != account_id
                or payload.get('session_id') != session_id
                or not isinstance(payload.get('id'), str)
            ):
                raise ValueError('Invalid cursor')
            timestamp = MentorCursor.timestamp(payload.get('created_at'))
            query = query.where(
                (MentorMessageModel.created_at < timestamp)
                | (
                    (MentorMessageModel.created_at == timestamp)
                    & (MentorMessageModel.id < payload['id'])
                )
            )

        models = list(
            self._session.scalars(
                query.order_by(
                    MentorMessageModel.created_at.desc(), MentorMessageModel.id.desc()
                ).limit(31)
            )
        )
        next_cursor = None
        if len(models) > 30:
            last = models[29]
            next_cursor = MentorCursor.encode(
                {
                    'kind': 'messages',
                    'account_id': account_id,
                    'session_id': session_id,
                    'created_at': last.created_at.isoformat(),
                    'id': last.id,
                }
            )
            models = models[:30]
        messages = [self._to_domain(model) for model in reversed(models)]
        return MentorMessagesPage(items=messages, next_cursor=next_cursor)

    def find_by_id(
        self, account_id: str, session_id: str, message_id: str
    ) -> MentorMessage | None:
        model = self._session.scalar(
            select(MentorMessageModel)
            .join(
                MentorSessionModel,
                MentorSessionModel.id == MentorMessageModel.session_id,
            )
            .where(
                MentorSessionModel.account_id == account_id,
                MentorSessionModel.id == session_id,
                MentorSessionModel.deleted_at.is_(None),
                MentorMessageModel.id == message_id,
            )
        )
        return self._to_domain(model) if model is not None else None

    def find_response(
        self, account_id: str, session_id: str, learner_message_id: str
    ) -> MentorMessage | None:
        model = self._session.scalar(
            select(MentorMessageModel)
            .join(
                MentorSessionModel,
                MentorSessionModel.id == MentorMessageModel.session_id,
            )
            .where(
                MentorSessionModel.account_id == account_id,
                MentorSessionModel.id == session_id,
                MentorSessionModel.deleted_at.is_(None),
                MentorMessageModel.in_reply_to_message_id == learner_message_id,
            )
        )
        return self._to_domain(model) if model is not None else None

    def find_pending_learner_message_id(
        self, account_id: str, session_id: str
    ) -> str | None:
        response = aliased(MentorMessageModel)
        return self._session.scalar(
            select(MentorMessageModel.id)
            .join(
                MentorSessionModel,
                MentorSessionModel.id == MentorMessageModel.session_id,
            )
            .outerjoin(
                response,
                response.in_reply_to_message_id == MentorMessageModel.id,
            )
            .where(
                MentorSessionModel.account_id == account_id,
                MentorSessionModel.id == session_id,
                MentorSessionModel.deleted_at.is_(None),
                MentorMessageModel.role == MentorMessageRole.LEARNER.value,
                response.id.is_(None),
            )
            .order_by(
                MentorMessageModel.created_at.desc(), MentorMessageModel.id.desc()
            )
            .limit(1)
        )

    def find_all(self, account_id: str, session_id: str) -> tuple[MentorMessage, ...]:
        models = self._session.scalars(
            select(MentorMessageModel)
            .join(
                MentorSessionModel,
                MentorSessionModel.id == MentorMessageModel.session_id,
            )
            .where(
                MentorSessionModel.account_id == account_id,
                MentorSessionModel.id == session_id,
                MentorSessionModel.deleted_at.is_(None),
            )
            .order_by(MentorMessageModel.created_at, MentorMessageModel.id)
        )
        return tuple(self._to_domain(model) for model in models)

    def measure_unsummarized(
        self,
        account_id: str,
        session_id: str,
        after: MentorSummaryBoundary | None,
        keep_recent: int,
    ) -> MentorMessageVolume:
        recent = (
            self._scoped(select(MentorMessageModel.id), account_id, session_id)
            .order_by(
                MentorMessageModel.created_at.desc(), MentorMessageModel.id.desc()
            )
            .limit(keep_recent)
            .correlate(None)
        )
        older = self._scoped(
            select(MentorMessageModel.id), account_id, session_id
        ).where(MentorMessageModel.id.not_in(recent))
        if after is not None:
            older = older.where(self._is_after(after))
        subquery = older.add_columns(
            MentorMessageModel.created_at,
            func.char_length(MentorMessageModel.content).label('characters'),
        ).subquery()
        count, characters = self._session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(subquery.c.characters), 0),
            ).select_from(subquery)
        ).one()
        newest = self._session.execute(
            older.add_columns(MentorMessageModel.created_at)
            .order_by(
                MentorMessageModel.created_at.desc(), MentorMessageModel.id.desc()
            )
            .limit(1)
        ).first()
        return MentorMessageVolume(
            count=int(count),
            characters=int(characters),
            last_message=(
                MentorSummaryBoundary(message_id=newest[0], created_at=newest[1])
                if newest is not None
                else None
            ),
        )

    def find_first_message_id(self, account_id: str, session_id: str) -> str | None:
        return self._session.scalar(
            self._scoped(select(MentorMessageModel.id), account_id, session_id)
            .order_by(MentorMessageModel.created_at, MentorMessageModel.id)
            .limit(1)
        )

    def find_range(
        self,
        account_id: str,
        session_id: str,
        after: MentorSummaryBoundary | None,
        until: MentorSummaryBoundary | None = None,
    ) -> tuple[MentorMessage, ...]:
        query = self._scoped(select(MentorMessageModel), account_id, session_id)
        if after is not None:
            query = query.where(self._is_after(after))
        if until is not None:
            query = query.where(~self._is_after(until))
        models = self._session.scalars(
            query.order_by(MentorMessageModel.created_at, MentorMessageModel.id)
        )
        return tuple(self._to_domain(model) for model in models)

    def find_by_ids(
        self, account_id: str, session_id: str, message_ids: tuple[str, ...]
    ) -> tuple[MentorMessage, ...]:
        if not message_ids:
            return ()
        models = self._session.scalars(
            self._scoped(select(MentorMessageModel), account_id, session_id)
            .where(MentorMessageModel.id.in_(message_ids))
            .order_by(MentorMessageModel.created_at, MentorMessageModel.id)
        )
        return tuple(self._to_domain(model) for model in models)

    @staticmethod
    def _scoped[Row: tuple[object, ...]](
        query: Select[Row], account_id: str, session_id: str
    ) -> Select[Row]:
        return query.join(
            MentorSessionModel,
            MentorSessionModel.id == MentorMessageModel.session_id,
        ).where(
            MentorSessionModel.account_id == account_id,
            MentorSessionModel.id == session_id,
            MentorSessionModel.deleted_at.is_(None),
        )

    @staticmethod
    def _is_after(boundary: MentorSummaryBoundary) -> ColumnElement[bool]:
        return (MentorMessageModel.created_at > boundary.created_at) | (
            (MentorMessageModel.created_at == boundary.created_at)
            & (MentorMessageModel.id > boundary.message_id)
        )

    def _to_domain(self, model: MentorMessageModel) -> MentorMessage:
        message = MentorMessageMapper.to_domain(model)
        attachments = self._session.scalars(
            select(MentorAttachmentModel)
            .where(
                MentorAttachmentModel.message_id == model.id,
                MentorAttachmentModel.session_id == model.session_id,
                MentorAttachmentModel.status != MentorAttachmentStatus.REMOVED.value,
            )
            .order_by(MentorAttachmentModel.created_at, MentorAttachmentModel.id)
        )
        return MentorMessage(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            in_reply_to_message_id=message.in_reply_to_message_id,
            attachments=tuple(
                MentorAttachmentView(
                    attachment_id=attachment.id,
                    filename=attachment.filename,
                    media_type=attachment.media_type,
                    size_bytes=attachment.size_bytes,
                    status=MentorAttachmentStatus(attachment.status),
                    failure_code=attachment.failure_code,
                    analyzed_pages=tuple(attachment.analyzed_pages),
                    illegible_pages=tuple(attachment.illegible_pages),
                    uninterpreted_pages=tuple(attachment.uninterpreted_pages),
                )
                for attachment in attachments
            ),
        )

    def add(self, message: MentorMessage) -> None:
        self._session.add(MentorMessageMapper.to_model(message))
        self._session.flush()

    def remove_by_session_id(self, session_id: str) -> None:
        self._session.execute(
            delete(MentorMessageModel).where(
                MentorMessageModel.session_id == session_id
            )
        )

    def remove_all(self) -> None:
        self._session.execute(delete(MentorMessageModel))

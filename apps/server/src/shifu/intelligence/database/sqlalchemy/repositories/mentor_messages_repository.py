from sqlalchemy import delete, select
from sqlalchemy.orm import Session, aliased

from shifu.intelligence.core.domain.entities import MentorMessage
from shifu.intelligence.core.domain.enums import MentorMessageRole
from shifu.intelligence.core.domain.structures import MentorMessagesPage
from shifu.intelligence.database.sqlalchemy.mappers import MentorMessageMapper
from shifu.intelligence.database.sqlalchemy.models import (
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
        messages = [MentorMessageMapper.to_domain(model) for model in reversed(models)]
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
        return MentorMessageMapper.to_domain(model) if model is not None else None

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
        return MentorMessageMapper.to_domain(model) if model is not None else None

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

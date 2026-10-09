import hashlib
from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.sql import Select
from sqlalchemy.orm import Session

from shifu.intelligence.core.domain.entities import MentorSession
from shifu.intelligence.core.domain.structures import (
    MentorSessionsPage,
    MentorSubmissionRecord,
)
from shifu.intelligence.database.sqlalchemy.mappers import MentorSessionMapper
from shifu.intelligence.database.sqlalchemy.models import MentorSessionModel
from shifu.intelligence.database.sqlalchemy.repositories.mentor_cursor import (
    MentorCursor,
)


class SqlalchemyMentorSessionsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_submission(
        self, account_id: str, submission_key: str
    ) -> MentorSubmissionRecord | None:
        model = self._session.scalar(
            select(MentorSessionModel).where(
                MentorSessionModel.account_id == account_id,
                MentorSessionModel.submission_key == submission_key,
            )
        )
        return self._to_submission(model) if model is not None else None

    def find_submission_by_session_id(
        self, account_id: str, session_id: str
    ) -> MentorSubmissionRecord | None:
        model = self._session.scalar(
            select(MentorSessionModel).where(
                MentorSessionModel.account_id == account_id,
                MentorSessionModel.id == session_id,
            )
        )
        return self._to_submission(model) if model is not None else None

    def lock_submission(self, account_id: str, submission_key: str) -> None:
        self._lock_advisory(f'{account_id}:{submission_key}')

    def lock_session(self, account_id: str, session_id: str) -> None:
        self._lock_advisory(f'session:{account_id}:{session_id}')

    def _lock_advisory(self, key: str) -> None:
        lock_key = hashlib.sha256(key.encode()).digest()[:8]
        advisory_key = int.from_bytes(lock_key, byteorder='big', signed=True)
        self._session.execute(select(func.pg_advisory_xact_lock(advisory_key)))

    def find_by_id(self, account_id: str, session_id: str) -> MentorSession | None:
        model = self._session.scalar(self._active_query(account_id, session_id))
        return MentorSessionMapper.to_domain(model) if model is not None else None

    def find_by_id_for_update(
        self, account_id: str, session_id: str
    ) -> MentorSession | None:
        model = self._session.scalar(
            self._active_query(account_id, session_id).with_for_update()
        )
        return MentorSessionMapper.to_domain(model) if model is not None else None

    def find_many(
        self, account_id: str, search: str | None, cursor: str | None
    ) -> MentorSessionsPage:
        query = select(MentorSessionModel).where(
            MentorSessionModel.account_id == account_id,
            MentorSessionModel.deleted_at.is_(None),
        )
        if search is not None:
            escaped = (
                search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            )
            query = query.where(
                MentorSessionModel.title_search.ilike(f'%{escaped}%', escape='\\')
            )
        if cursor is not None:
            payload = MentorCursor.decode(cursor)
            if (
                payload.get('kind') != 'sessions'
                or payload.get('account_id') != account_id
                or payload.get('search') != search
                or not isinstance(payload.get('id'), str)
            ):
                raise ValueError('Invalid cursor')
            timestamp = MentorCursor.timestamp(payload.get('activity_at'))
            query = query.where(
                (MentorSessionModel.last_activity_at < timestamp)
                | (
                    (MentorSessionModel.last_activity_at == timestamp)
                    & (MentorSessionModel.id < payload['id'])
                )
            )

        models = list(
            self._session.scalars(
                query.order_by(
                    MentorSessionModel.last_activity_at.desc(),
                    MentorSessionModel.id.desc(),
                ).limit(31)
            )
        )
        next_cursor = None
        if len(models) > 30:
            last = models[29]
            if last.last_activity_at is None:
                raise ValueError('An active Mentor session has no activity timestamp')
            next_cursor = MentorCursor.encode(
                {
                    'kind': 'sessions',
                    'account_id': account_id,
                    'search': search,
                    'activity_at': last.last_activity_at.isoformat(),
                    'id': last.id,
                }
            )
            models = models[:30]
        return MentorSessionsPage(
            items=[MentorSessionMapper.to_domain(model) for model in models],
            next_cursor=next_cursor,
        )

    def add(
        self, session: MentorSession, submission_key: str, content_fingerprint: str
    ) -> None:
        self._session.add(
            MentorSessionMapper.to_model(session, submission_key, content_fingerprint)
        )
        self._session.flush()

    def rename(self, session: MentorSession) -> None:
        self._session.execute(
            update(MentorSessionModel)
            .where(
                MentorSessionModel.id == session.id,
                MentorSessionModel.account_id == session.account_id,
                MentorSessionModel.deleted_at.is_(None),
            )
            .values(
                title=session.title,
                title_search=MentorSessionMapper.to_search_title(session.title),
                updated_at=session.updated_at,
            )
        )

    def record_activity(self, session: MentorSession) -> None:
        self._session.execute(
            update(MentorSessionModel)
            .where(
                MentorSessionModel.id == session.id,
                MentorSessionModel.account_id == session.account_id,
                MentorSessionModel.deleted_at.is_(None),
            )
            .values(
                updated_at=session.updated_at, last_activity_at=session.last_activity_at
            )
        )

    def remove(self, session: MentorSession, deleted_at: datetime) -> None:
        self._session.execute(
            update(MentorSessionModel)
            .where(
                MentorSessionModel.id == session.id,
                MentorSessionModel.account_id == session.account_id,
                MentorSessionModel.deleted_at.is_(None),
            )
            .values(
                title=None,
                title_search=None,
                content_fingerprint=None,
                created_at=None,
                updated_at=None,
                last_activity_at=None,
                deleted_at=deleted_at,
            )
        )

    def _active_query(
        self, account_id: str, session_id: str
    ) -> Select[tuple[MentorSessionModel]]:
        return select(MentorSessionModel).where(
            MentorSessionModel.account_id == account_id,
            MentorSessionModel.id == session_id,
            MentorSessionModel.deleted_at.is_(None),
        )

    @staticmethod
    def _to_submission(model: MentorSessionModel) -> MentorSubmissionRecord:
        return MentorSubmissionRecord(
            session_id=model.id,
            content_fingerprint=model.content_fingerprint,
            deleted_at=model.deleted_at,
        )

    def remove_all(self) -> None:
        self._session.execute(delete(MentorSessionModel))

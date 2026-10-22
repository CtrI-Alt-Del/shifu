from sqlalchemy import select, delete, func, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

from shifu.intelligence.core.domain.structures import (
    MentorResponseEvent,
    MentorResponseSnapshot,
)
from shifu.intelligence.core.domain.enums import (
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.database.sqlalchemy.models import (
    MentorResponseEventModel,
    MentorResponseAttemptModel,
    MentorSessionModel,
)
from shifu.intelligence.database.sqlalchemy.mappers import MentorResponseEventMapper


class SqlalchemyMentorResponseEventsRepository:
    def __init__(self, session: Session) -> None:
        self._session: Session = session

    def append(self, event: MentorResponseEvent) -> None:
        self._session.add(MentorResponseEventMapper.to_model(event))
        self._session.flush()

    def next_sequence(self, session_id: str) -> int:
        try:
            return self._session.execute(
                update(MentorSessionModel)
                .where(MentorSessionModel.id == session_id)
                .values(response_sequence=MentorSessionModel.response_sequence + 1)
                .returning(MentorSessionModel.response_sequence)
            ).scalar_one()
        except NoResultFound:
            raise ValueError('Missing response session') from None

    def find_after(
        self, account_id: str, session_id: str, sequence: int
    ) -> tuple[MentorResponseEvent, ...]:
        models = self._session.scalars(
            select(MentorResponseEventModel)
            .join(
                MentorSessionModel,
                MentorSessionModel.id == MentorResponseEventModel.session_id,
            )
            .where(
                MentorSessionModel.account_id == account_id,
                MentorSessionModel.deleted_at.is_(None),
                MentorResponseEventModel.session_id == session_id,
                MentorResponseEventModel.sequence > sequence,
            )
            .order_by(MentorResponseEventModel.sequence)
        )
        return tuple(MentorResponseEventMapper.to_structure(model) for model in models)

    def snapshot(
        self, account_id: str, session_id: str
    ) -> MentorResponseSnapshot | None:
        attempt = self._session.scalar(
            select(MentorResponseAttemptModel)
            .where(
                MentorResponseAttemptModel.account_id == account_id,
                MentorResponseAttemptModel.session_id == session_id,
            )
            .order_by(
                MentorResponseAttemptModel.created_at.desc(),
                MentorResponseAttemptModel.id.desc(),
            )
            .limit(1)
        )
        if attempt is None:
            return None
        events = tuple(
            event
            for event in self.find_after(account_id, session_id, 0)
            if event.attempt_id == attempt.id
        )
        blocks = tuple(
            sorted(
                (event.block for event in events if event.block is not None),
                key=lambda block: block.ordinal,
            )
        )
        consultations = tuple(
            event.consultation for event in events if event.consultation is not None
        )
        sequence = (
            self._session.scalar(
                select(func.max(MentorResponseEventModel.sequence)).where(
                    MentorResponseEventModel.session_id == session_id
                )
            )
            or 0
        )
        failure = next(
            (event.failure_code for event in reversed(events) if event.failure_code),
            None,
        )
        status_events = tuple(
            event for event in events if event.kind is MentorResponseEventKind.STATUS
        )
        # The progress of a response is the progress of its latest status event;
        # a status event without progress clears it.
        progress = (
            status_events[-1].progress
            if status_events and attempt.status == MentorResponseStatus.PROCESSING
            else None
        )
        return MentorResponseSnapshot(
            attempt_id=attempt.id,
            learner_message_id=attempt.learner_message_id,
            status=MentorResponseStatus(attempt.status),
            blocks=blocks,
            consultations=consultations,
            last_sequence=sequence,
            failure_code=failure,
            progress=progress,
        )

    def discard_partial(self, attempt_id: str) -> None:
        self._session.execute(
            delete(MentorResponseEventModel).where(
                MentorResponseEventModel.attempt_id == attempt_id,
                MentorResponseEventModel.kind.in_(['block', 'consultation']),
            )
        )

    def remove_by_session_id(self, session_id: str) -> None:
        self._session.execute(
            delete(MentorResponseEventModel).where(
                MentorResponseEventModel.session_id == session_id
            )
        )

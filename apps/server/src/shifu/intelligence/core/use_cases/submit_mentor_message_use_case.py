from uuid import UUID

from shifu.intelligence.core.domain.entities import MentorMessage, MentorResponseAttempt
from shifu.intelligence.core.domain.enums import (
    MentorMessageRole,
    MentorResponseStatus,
    MentorResponseEventKind,
)
from shifu.intelligence.core.domain.errors import (
    MentorInputInvalidError,
    MentorSessionNotFoundError,
    MentorResponseConflictError,
    MentorSubmissionConflictError,
)
from shifu.intelligence.core.domain.events import (
    MentorResponseRequestedEvent,
    MentorResponseRequestedPayload,
)
from shifu.intelligence.core.domain.structures import (
    MentorSubmission,
    MentorSessionDetail,
    MentorResponseEvent,
)
from shifu.intelligence.core.domain.structures.mentor_submission_fingerprint import (
    mentor_submission_fingerprint,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
)


class SubmitMentorMessageUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        identifier_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self.replayed: bool = False
        self._database: IntelligenceDatabase = database
        self._identifier_provider: IdentifierProvider = identifier_provider
        self._clock_provider: ClockProvider = clock_provider
        self._access_provider: MentorAccessProvider = access_provider

    def execute(
        self, account_id: str, session_id: str, submission: MentorSubmission
    ) -> MentorSessionDetail:
        self._validate(submission)
        fingerprint = mentor_submission_fingerprint(
            submission.content, submission.context_hint
        )
        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id_for_update(
                account_id, session_id
            )
            if session is None:
                raise MentorSessionNotFoundError
            replay = repositories.mentor_response_attempts.find_submission(
                account_id, session_id, submission.submission_key
            )
            if replay is not None:
                self.replayed = True
                if replay[1] != fingerprint:
                    raise MentorSubmissionConflictError
                self._access_provider.assert_current(
                    self._access_provider.authorize(account_id, replay[0].operation_key)
                )
            else:
                if (
                    repositories.mentor_messages.find_pending_learner_message_id(
                        account_id, session_id
                    )
                    is not None
                ):
                    raise MentorResponseConflictError
                grant = self._access_provider.authorize(
                    account_id, submission.submission_key
                )
                self._access_provider.assert_current(grant)
                now = self._clock_provider.now()
                message = MentorMessage(
                    id=self._identifier_provider.generate(),
                    session_id=session_id,
                    role=MentorMessageRole.LEARNER,
                    content=submission.content,
                    created_at=now,
                    in_reply_to_message_id=None,
                )
                attempt = MentorResponseAttempt.create(
                    id=self._identifier_provider.generate(),
                    account_id=account_id,
                    session_id=session_id,
                    learner_message_id=message.id,
                    status=MentorResponseStatus.QUEUED,
                    context_hint=submission.context_hint,
                    access_revision=grant.access_revision,
                    operation_key=grant.operation_key,
                    created_at=now,
                    updated_at=now,
                )
                repositories.mentor_messages.add(message)
                repositories.mentor_response_attempts.add(attempt)
                repositories.mentor_response_attempts.add_submission(
                    account_id,
                    session_id,
                    submission.submission_key,
                    attempt.id,
                    fingerprint,
                )
                repositories.mentor_response_events.append(
                    MentorResponseEvent(
                        session_id=session_id,
                        attempt_id=attempt.id,
                        sequence=repositories.mentor_response_events.next_sequence(
                            session_id
                        ),
                        kind=MentorResponseEventKind.STATUS,
                        status=MentorResponseStatus.QUEUED,
                        block=None,
                        consultation=None,
                        failure_code=None,
                        created_at=now,
                    )
                )
                repositories.events.add(
                    MentorResponseRequestedEvent(
                        payload=MentorResponseRequestedPayload(attempt_id=attempt.id)
                    )
                )
                session.updated_at = now
                session.last_activity_at = now
                repositories.mentor_sessions.record_activity(session)
            return MentorSessionDetail(
                session=session,
                messages=repositories.mentor_messages.find_many(
                    account_id, session_id, None
                ),
                pending_learner_message_id=repositories.mentor_messages.find_pending_learner_message_id(
                    account_id, session_id
                ),
                response=repositories.mentor_response_events.snapshot(
                    account_id, session_id
                ),
            )

    @staticmethod
    def _validate(submission: MentorSubmission) -> None:
        if not submission.content.strip():
            raise MentorInputInvalidError
        try:
            parsed = UUID(submission.submission_key)
        except ValueError as error:
            raise MentorInputInvalidError from error
        if parsed.version != 4 or str(parsed) != submission.submission_key.lower():
            raise MentorInputInvalidError

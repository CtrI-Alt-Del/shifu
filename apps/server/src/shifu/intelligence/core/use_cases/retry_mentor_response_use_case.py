from shifu.intelligence.core.domain.entities import MentorResponseAttempt
from shifu.intelligence.core.domain.enums import (
    MentorResponseStatus,
    MentorResponseEventKind,
)
from shifu.intelligence.core.domain.errors import (
    MentorSessionNotFoundError,
    MentorResponseConflictError,
    MentorSubmissionConflictError,
)
from shifu.intelligence.core.domain.structures import (
    MentorResponseSnapshot,
    MentorResponseEvent,
    MentorSubmission,
)
from shifu.intelligence.core.domain.events import (
    MentorResponseRequestedEvent,
    MentorResponseRequestedPayload,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
)


class RetryMentorResponseUseCase:
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
        self, account_id: str, session_id: str, attempt_id: str, submission_key: str
    ) -> MentorResponseSnapshot:
        MentorSubmission(submission_key=submission_key, content='retry')
        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id_for_update(
                account_id, session_id
            )
            if session is None:
                raise MentorSessionNotFoundError
            attempt = repositories.mentor_response_attempts.find_by_id_for_update(
                attempt_id
            )
            current = repositories.mentor_response_attempts.find_current(
                account_id, session_id
            )
            if (
                attempt is None
                or current is None
                or attempt.account_id != account_id
                or attempt.session_id != session_id
            ):
                raise MentorSessionNotFoundError
            replay = repositories.mentor_response_attempts.find_submission(
                account_id, session_id, submission_key
            )
            fingerprint = 'retry:' + attempt_id
            grant = self._access_provider.authorize(account_id, attempt.operation_key)
            self._access_provider.assert_current(grant)
            if replay is not None:
                self.replayed = True
                if replay[1] != fingerprint:
                    raise MentorSubmissionConflictError
            else:
                if current.id != attempt_id or attempt.status not in (
                    MentorResponseStatus.FAILED,
                    MentorResponseStatus.CANCELLED,
                ):
                    raise MentorResponseConflictError
                now = self._clock_provider.now()
                retry = MentorResponseAttempt.create(
                    id=self._identifier_provider.generate(),
                    account_id=account_id,
                    session_id=session_id,
                    learner_message_id=attempt.learner_message_id,
                    status=MentorResponseStatus.QUEUED,
                    context_hint=attempt.context_hint,
                    access_revision=grant.access_revision,
                    operation_key=attempt.operation_key,
                    created_at=now,
                    updated_at=now,
                )
                repositories.mentor_response_events.discard_partial(attempt.id)
                repositories.mentor_response_attempts.add(retry)
                repositories.mentor_response_attempts.add_submission(
                    account_id, session_id, submission_key, retry.id, fingerprint
                )
                repositories.mentor_response_events.append(
                    MentorResponseEvent(
                        session_id=session_id,
                        attempt_id=retry.id,
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
                        payload=MentorResponseRequestedPayload(attempt_id=retry.id)
                    )
                )
            snapshot = repositories.mentor_response_events.snapshot(
                account_id, session_id
            )
            if snapshot is None:
                raise MentorResponseConflictError
            return snapshot

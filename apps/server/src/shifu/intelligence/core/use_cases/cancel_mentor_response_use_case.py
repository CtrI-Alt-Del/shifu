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
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class CancelMentorResponseUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self._database: IntelligenceDatabase = database
        self._clock_provider: ClockProvider = clock_provider
        self._access_provider: MentorAccessProvider = access_provider

    def execute(
        self, account_id: str, session_id: str, attempt_id: str, submission_key: str
    ) -> MentorResponseSnapshot:
        MentorSubmission(submission_key=submission_key, content='cancel')
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
            grant = MentorAccessGrant(
                account_id=account_id,
                access_revision=attempt.access_revision,
                operation_key=attempt.operation_key,
            )
            self._access_provider.assert_current(grant)
            replay = repositories.mentor_response_attempts.find_submission(
                account_id, session_id, submission_key
            )
            fingerprint = 'cancel:' + attempt_id
            if replay is not None:
                if replay[1] != fingerprint:
                    raise MentorSubmissionConflictError
            else:
                if current.id != attempt_id or attempt.status not in (
                    MentorResponseStatus.QUEUED,
                    MentorResponseStatus.PROCESSING,
                ):
                    raise MentorResponseConflictError
                if not repositories.mentor_response_attempts.transition(
                    attempt.id,
                    attempt.status,
                    MentorResponseStatus.CANCELLED,
                    grant.access_revision,
                ):
                    raise MentorResponseConflictError
                repositories.mentor_response_events.discard_partial(attempt.id)
                repositories.mentor_response_attempts.add_submission(
                    account_id, session_id, submission_key, attempt.id, fingerprint
                )
                repositories.mentor_response_events.append(
                    MentorResponseEvent(
                        session_id=session_id,
                        attempt_id=attempt.id,
                        sequence=repositories.mentor_response_events.next_sequence(
                            session_id
                        ),
                        kind=MentorResponseEventKind.CANCELLED,
                        status=MentorResponseStatus.CANCELLED,
                        block=None,
                        consultation=None,
                        failure_code=None,
                        created_at=self._clock_provider.now(),
                    )
                )
            snapshot = repositories.mentor_response_events.snapshot(
                account_id, session_id
            )
            if snapshot is None:
                raise MentorResponseConflictError
            return snapshot

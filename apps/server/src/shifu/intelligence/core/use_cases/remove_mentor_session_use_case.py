from shifu.intelligence.core.domain.errors import MentorSessionNotFoundError
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases.remove_mentor_attachment_use_case import (
    revoke_session_attachments,
)
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class RemoveMentorSessionUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider
        self._access_provider = access_provider

    def execute(self, account_id: str, session_id: str) -> None:
        with self._database.transaction() as repositories:
            submission = repositories.mentor_sessions.find_submission_by_session_id(
                account_id, session_id
            )
            if submission is None:
                raise MentorSessionNotFoundError

            repositories.mentor_sessions.lock_session(account_id, session_id)
            repositories.learner_memory_changes.remove_by_session_id(session_id)
            current_submission = (
                repositories.mentor_sessions.find_submission_by_session_id(
                    account_id, session_id
                )
            )
            if current_submission is None:
                raise MentorSessionNotFoundError
            if current_submission.deleted_at is not None:
                return

            session = repositories.mentor_sessions.find_by_id_for_update(
                account_id, session_id
            )
            if session is None:
                raise MentorSessionNotFoundError

            repositories.mentor_session_summaries.remove_by_session_id(session.id)
            revoke_session_attachments(
                repositories,
                self._access_provider,
                account_id,
                session_id,
                self._clock_provider.now(),
            )
            repositories.mentor_action_proposals.remove_by_session_id(
                account_id, session.id
            )
            repositories.mentor_response_events.remove_by_session_id(session.id)
            repositories.mentor_response_attempts.remove_by_session_id(session.id)
            repositories.mentor_messages.remove_by_session_id(session.id)
            repositories.mentor_sessions.remove(session, self._clock_provider.now())

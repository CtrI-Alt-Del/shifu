from shifu.intelligence.core.interfaces import IntelligenceDatabaseRepositories
from shifu.shared.core.interfaces import MentorAccessProvider
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.intelligence.core.domain.enums import (
    MentorResponseStatus,
    MentorResponseEventKind,
)
from shifu.intelligence.core.domain.structures import MentorResponseEvent
from shifu.intelligence.core.domain.entities import MentorMessage, MentorResponseAttempt
from shifu.intelligence.core.domain.enums import MentorMessageRole
from shifu.intelligence.core.domain.errors import MentorResponseConflictError
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class FinalizeMentorResponseUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        identifier_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self._access_provider: MentorAccessProvider = access_provider
        self._database = database
        self._identifier_provider = identifier_provider
        self._clock_provider = clock_provider

    def execute(
        self,
        account_id: str,
        session_id: str,
        learner_message_id: str,
        content: str,
        attempt_id: str,
        execution_owner: str | None = None,
    ) -> bool:
        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id_for_update(
                account_id, session_id
            )
            if session is None:
                return False

            attempt = repositories.mentor_response_attempts.find_by_id_for_update(
                attempt_id
            )
            current = repositories.mentor_response_attempts.find_current(
                account_id, session_id
            )
            if (
                attempt is None
                or current is None
                or current.id != attempt_id
                or attempt.account_id != account_id
                or attempt.session_id != session_id
                or attempt.learner_message_id != learner_message_id
            ):
                return False
            if attempt.status not in (
                MentorResponseStatus.PROCESSING,
                MentorResponseStatus.COMPLETED,
            ) or not self._owns_execution(repositories, attempt, execution_owner):
                return False
            self._access_provider.assert_current(
                MentorAccessGrant(
                    account_id=account_id,
                    access_revision=attempt.access_revision,
                    operation_key=attempt.operation_key,
                )
            )

            learner_message = repositories.mentor_messages.find_by_id(
                account_id, session_id, learner_message_id
            )
            if learner_message is None:
                return False
            if learner_message.role is not MentorMessageRole.LEARNER:
                raise MentorResponseConflictError

            response = repositories.mentor_messages.find_response(
                account_id, session_id, learner_message_id
            )
            if response is not None:
                if response.content != content:
                    raise MentorResponseConflictError
                return True

            if not self._verify_approved(
                repositories, account_id, session_id, attempt_id, content
            ):
                return False
            if not repositories.mentor_response_attempts.transition(
                attempt.id,
                MentorResponseStatus.PROCESSING,
                MentorResponseStatus.COMPLETED,
                attempt.access_revision,
            ):
                return False
            now = self._clock_provider.now()
            repositories.mentor_messages.add(
                MentorMessage(
                    id=self._identifier_provider.generate(),
                    session_id=session_id,
                    role=MentorMessageRole.MENTOR,
                    content=content,
                    created_at=now,
                    in_reply_to_message_id=learner_message_id,
                )
            )
            repositories.mentor_response_events.append(
                MentorResponseEvent(
                    session_id=session_id,
                    attempt_id=attempt.id,
                    sequence=repositories.mentor_response_events.next_sequence(
                        session_id
                    ),
                    kind=MentorResponseEventKind.COMPLETED,
                    status=MentorResponseStatus.COMPLETED,
                    block=None,
                    consultation=None,
                    failure_code=None,
                    created_at=now,
                )
            )
            session.updated_at = now
            session.last_activity_at = now
            repositories.mentor_sessions.record_activity(session)
            return True

    def _owns_execution(
        self,
        repositories: IntelligenceDatabaseRepositories,
        attempt: MentorResponseAttempt,
        execution_owner: str | None,
    ) -> bool:
        if attempt.status is MentorResponseStatus.COMPLETED:
            return True
        return (
            execution_owner is not None
            and repositories.mentor_response_attempts.has_claim(
                attempt.id, execution_owner, self._clock_provider.now()
            )
        )

    @staticmethod
    def _verify_approved(
        repositories: IntelligenceDatabaseRepositories,
        account_id: str,
        session_id: str,
        attempt_id: str,
        content: str,
    ) -> bool:
        snapshot = repositories.mentor_response_events.snapshot(account_id, session_id)
        if snapshot is None or snapshot.attempt_id != attempt_id or not snapshot.blocks:
            return False
        approved_content = '\n\n'.join(
            block.content
            for block in sorted(snapshot.blocks, key=lambda block: block.ordinal)
        )
        if content != approved_content:
            raise MentorResponseConflictError
        return True

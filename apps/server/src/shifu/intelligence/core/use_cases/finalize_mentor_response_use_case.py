from shifu.intelligence.core.domain.entities import MentorMessage
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
    ) -> None:
        self._database = database
        self._identifier_provider = identifier_provider
        self._clock_provider = clock_provider

    def execute(
        self,
        account_id: str,
        session_id: str,
        learner_message_id: str,
        content: str,
    ) -> bool:
        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id_for_update(
                account_id, session_id
            )
            if session is None:
                return False

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
            session.updated_at = now
            session.last_activity_at = now
            repositories.mentor_sessions.record_activity(session)
            return True

import hashlib
from uuid import UUID

from shifu.intelligence.core.domain.entities import MentorMessage, MentorSession
from shifu.intelligence.core.domain.enums import MentorMessageRole
from shifu.intelligence.core.interfaces import (
    MentorMessagesRepository,
    MentorSessionsRepository,
)


class IntelligenceSeeder:
    def __init__(
        self,
        sessions_repository: MentorSessionsRepository,
        messages_repository: MentorMessagesRepository,
    ) -> None:
        self._sessions_repository: MentorSessionsRepository = sessions_repository
        self._messages_repository: MentorMessagesRepository = messages_repository

    def clear(self) -> None:
        self._messages_repository.remove_all()
        self._sessions_repository.remove_all()

    def run(self, sessions: list[MentorSession], messages: list[MentorMessage]) -> None:
        for session in sessions:
            first_message = min(
                (
                    message
                    for message in messages
                    if message.session_id == session.id
                    and message.role == MentorMessageRole.LEARNER
                ),
                key=lambda message: (message.created_at, message.id),
            )
            submission_key = str(
                UUID(bytes=hashlib.sha256(session.id.encode()).digest()[:16], version=4)
            )
            fingerprint = hashlib.sha256(first_message.content.encode()).hexdigest()
            self._sessions_repository.add(session, submission_key, fingerprint)

        for message in sorted(messages, key=lambda item: (item.created_at, item.id)):
            self._messages_repository.add(message)

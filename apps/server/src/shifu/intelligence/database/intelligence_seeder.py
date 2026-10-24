import hashlib
from uuid import UUID

from shifu.intelligence.core.domain.entities import (
    LearnerMemory,
    MentorMessage,
    MentorSession,
)
from shifu.intelligence.core.domain.enums import MentorMessageRole
from shifu.intelligence.core.domain.structures import (
    LearnerMemoryDetails,
    LearnerMemoryOrigin,
)
from shifu.intelligence.core.interfaces import (
    LearnerMemoriesRepository,
    LearnerMemoryChangesRepository,
    MentorMessagesRepository,
    MentorSessionsRepository,
)
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.providers.system_clock_provider import SystemClockProvider


class IntelligenceSeeder:
    def __init__(
        self,
        sessions_repository: MentorSessionsRepository,
        messages_repository: MentorMessagesRepository,
        memories_repository: LearnerMemoriesRepository,
        memory_changes_repository: LearnerMemoryChangesRepository,
        clock_provider: ClockProvider | None = None,
    ) -> None:
        self._sessions_repository: MentorSessionsRepository = sessions_repository
        self._messages_repository: MentorMessagesRepository = messages_repository
        self._memories_repository: LearnerMemoriesRepository = memories_repository
        self._memory_changes_repository: LearnerMemoryChangesRepository = (
            memory_changes_repository
        )
        self._clock_provider: ClockProvider = clock_provider or SystemClockProvider()

    def clear(self) -> None:
        # Memory data references messages and sessions, so it is removed first.
        self._memory_changes_repository.remove_all()
        self._memories_repository.remove_all()
        self._messages_repository.remove_all()
        self._sessions_repository.remove_all()

    def run(
        self,
        sessions: list[MentorSession],
        messages: list[MentorMessage],
        memories: list[LearnerMemoryDetails] | None = None,
        tombstoned_session_ids: list[str] | None = None,
    ) -> None:
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

        for details in memories or []:
            self._add_memory(details)

        # Deleting a conversation keeps its memories with an unavailable origin.
        for session in sessions:
            if session.id in (tombstoned_session_ids or []):
                self._messages_repository.remove_by_session_id(session.id)
                self._sessions_repository.remove(session, self._clock_provider.now())

    def _add_memory(self, details: LearnerMemoryDetails) -> None:
        memory: LearnerMemory = details.memory
        first, *others = details.origins
        self._memories_repository.add(
            memory,
            details.concepts,
            LearnerMemoryOrigin(
                session_id=first.session_id,
                message_id=first.message_id,
                declared_at=first.declared_at,
            ),
        )
        for origin in others:
            self._memories_repository.add_origin(
                memory.id,
                LearnerMemoryOrigin(
                    session_id=origin.session_id,
                    message_id=origin.message_id,
                    declared_at=origin.declared_at,
                ),
            )

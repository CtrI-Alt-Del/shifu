from contextlib import AbstractContextManager
from typing import Protocol

from shifu.intelligence.core.interfaces.mentor_attachment_batches_repository import (
    MentorAttachmentBatchesRepository,
)
from shifu.intelligence.core.interfaces.mentor_attachment_chunks_repository import (
    MentorAttachmentChunksRepository,
)
from shifu.intelligence.core.interfaces.mentor_attachments_repository import (
    MentorAttachmentsRepository,
)
from shifu.intelligence.core.interfaces.mentor_embeddings_repository import (
    MentorEmbeddingsRepository,
)
from shifu.intelligence.core.interfaces.mentor_messages_repository import (
    MentorMessagesRepository,
)
from shifu.intelligence.core.interfaces.mentor_response_attempts_repository import (
    MentorResponseAttemptsRepository,
)
from shifu.intelligence.core.interfaces.mentor_response_events_repository import (
    MentorResponseEventsRepository,
)
from shifu.intelligence.core.interfaces.mentor_session_summaries_repository import (
    MentorSessionSummariesRepository,
)
from shifu.intelligence.core.interfaces.mentor_sessions_repository import (
    MentorSessionsRepository,
)
from shifu.intelligence.core.interfaces.planning_sessions_repository import (
    PlanningSessionsRepository,
)
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.interfaces import EventsRepository


@structure
class IntelligenceDatabaseRepositories:
    planning_sessions: PlanningSessionsRepository
    events: EventsRepository
    mentor_sessions: MentorSessionsRepository
    mentor_embeddings: MentorEmbeddingsRepository
    mentor_messages: MentorMessagesRepository
    mentor_response_attempts: MentorResponseAttemptsRepository
    mentor_response_events: MentorResponseEventsRepository
    mentor_attachment_batches: MentorAttachmentBatchesRepository
    mentor_attachments: MentorAttachmentsRepository
    mentor_attachment_chunks: MentorAttachmentChunksRepository
    mentor_session_summaries: MentorSessionSummariesRepository


class IntelligenceDatabase(Protocol):
    def transaction(
        self,
    ) -> AbstractContextManager[IntelligenceDatabaseRepositories]:
        """Open the sole transaction boundary for one Intelligence operation."""
        ...

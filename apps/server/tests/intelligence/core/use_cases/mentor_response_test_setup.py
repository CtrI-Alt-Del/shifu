from datetime import UTC, datetime
from unittest.mock import Mock, create_autospec

from shifu.intelligence.core.domain.entities import (
    MentorMessage,
    MentorResponseAttempt,
    MentorSession,
)
from shifu.intelligence.core.domain.enums import MentorMessageRole, MentorResponseStatus
from shifu.intelligence.core.domain.structures import (
    MentorMessagesPage,
    MentorResponseSnapshot,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    LearnerMemoriesRepository,
    LearnerMemoryChangesRepository,
    MentorActionProposalsRepository,
    MentorMessagesRepository,
    MentorResponseAttemptsRepository,
    MentorResponseEventsRepository,
    MentorSessionsRepository,
    MentorSessionSummariesRepository,
)
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import (
    ClockProvider,
    EventsRepository,
    IdentifierProvider,
    MentorAccessProvider,
)


class MentorResponseTestSetup:
    database: Mock
    repositories: Mock
    clock: Mock
    identifiers: Mock
    access: Mock
    now: datetime
    attempt: MentorResponseAttempt
    snapshot: MentorResponseSnapshot
    session: MentorSession
    message: MentorMessage
    key: str = '123e4567-e89b-42d3-a456-426614174000'

    def prepare(
        self, status: MentorResponseStatus = MentorResponseStatus.PROCESSING
    ) -> None:
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        for name, port in [
            ('mentor_response_attempts', MentorResponseAttemptsRepository),
            ('mentor_response_events', MentorResponseEventsRepository),
            ('mentor_messages', MentorMessagesRepository),
            ('mentor_sessions', MentorSessionsRepository),
            ('mentor_session_summaries', MentorSessionSummariesRepository),
            ('learner_memories', LearnerMemoriesRepository),
            ('learner_memory_changes', LearnerMemoryChangesRepository),
            ('mentor_action_proposals', MentorActionProposalsRepository),
            ('events', EventsRepository),
        ]:
            setattr(self.repositories, name, create_autospec(port, instance=True))
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.now = datetime(2026, 10, 10, tzinfo=UTC)
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = self.now
        self.identifiers = create_autospec(IdentifierProvider, instance=True)
        self.identifiers.generate.side_effect = [
            'message-new',
            'attempt-new',
            'final-response',
        ]
        self.access = create_autospec(MentorAccessProvider, instance=True)
        self.access.authorize.return_value = MentorAccessGrant(
            account_id='account', access_revision='revision', operation_key='operation'
        )
        self.attempt = MentorResponseAttempt(
            id='attempt',
            account_id='account',
            session_id='session',
            learner_message_id='message',
            status=status,
            context_hint=None,
            access_revision='revision',
            operation_key='operation',
            created_at=self.now,
            updated_at=self.now,
        )
        self.snapshot = MentorResponseSnapshot(
            attempt_id='attempt',
            learner_message_id='message',
            status=status,
            blocks=(),
            consultations=(),
            last_sequence=1,
            failure_code=None,
        )
        self.session = MentorSession(
            id='session',
            account_id='account',
            title='Conversa',
            created_at=self.now,
            updated_at=self.now,
            last_activity_at=self.now,
        )
        self.message = MentorMessage(
            id='message',
            session_id='session',
            role=MentorMessageRole.LEARNER,
            content='  pergunta exata  ',
            created_at=self.now,
            in_reply_to_message_id=None,
        )
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = (
            self.session
        )
        self.repositories.mentor_sessions.find_by_id.return_value = self.session
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = self.attempt
        self.repositories.mentor_response_attempts.find_by_id.return_value = (
            self.attempt
        )
        self.repositories.mentor_response_attempts.find_current.return_value = (
            self.attempt
        )
        self.repositories.mentor_response_attempts.find_submission.return_value = None
        self.repositories.mentor_response_attempts.transition.return_value = True
        self.repositories.mentor_response_attempts.claim.return_value = True
        self.repositories.mentor_response_attempts.has_claim.return_value = True
        self.repositories.mentor_response_attempts.find_continuity.return_value = ()
        self.repositories.mentor_response_attempts.update_references.return_value = True
        self.repositories.mentor_response_attempts.reserve_generation.return_value = (
            True
        )
        self.repositories.mentor_response_events.snapshot.return_value = self.snapshot
        self.repositories.mentor_response_events.next_sequence.return_value = 2
        self.repositories.mentor_messages.find_all.return_value = (self.message,)
        self.repositories.mentor_messages.find_by_id.return_value = self.message
        self.repositories.mentor_attachments.find_by_message_id.return_value = ()
        self.repositories.mentor_messages.find_response.return_value = None
        self.repositories.mentor_messages.find_many.return_value = MentorMessagesPage(
            items=[self.message], next_cursor=None
        )
        self.repositories.mentor_messages.find_pending_learner_message_id.return_value = None
        self.repositories.mentor_action_proposals.find_many_by_session.return_value = []
        self.repositories.mentor_action_proposals.exists_pending.return_value = False
        self.repositories.mentor_session_summaries.find_ready.return_value = None
        self.repositories.mentor_session_summaries.find_failed.return_value = None
        self.repositories.mentor_session_summaries.find_processing_for_update.return_value = None

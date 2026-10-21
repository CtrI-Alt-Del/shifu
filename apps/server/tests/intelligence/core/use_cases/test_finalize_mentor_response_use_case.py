from shifu.intelligence.core.domain.structures import (
    MentorResponseBlock,
    MentorResponseSnapshot,
    MentorResponseEvent,
)
from shifu.shared.core.interfaces import MentorAccessProvider
from shifu.shared.core.domain.structures import MentorAccessGrant
from dataclasses import replace
from shifu.intelligence.core.domain.entities import MentorResponseAttempt
from shifu.intelligence.core.domain.enums import (
    MentorResponseStatus,
    MentorResponseEventKind,
)
from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.entities import MentorMessage, MentorSession
from shifu.intelligence.core.domain.enums import MentorMessageRole
from shifu.intelligence.core.domain.errors import MentorResponseConflictError
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases import FinalizeMentorResponseUseCase
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class TestFinalizeMentorResponseUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.now = datetime(2026, 1, 1, tzinfo=UTC)
        self.session = MentorSession(
            id='session',
            account_id='account',
            title='title',
            created_at=self.now,
            updated_at=self.now,
            last_activity_at=self.now,
        )
        self.learner_message = MentorMessage(
            id='learner-message',
            session_id='session',
            role=MentorMessageRole.LEARNER,
            content='question',
            created_at=self.now,
            in_reply_to_message_id=None,
        )
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = (
            self.session
        )
        self.repositories.mentor_messages.find_by_id.return_value = self.learner_message
        self.repositories.mentor_messages.find_response.return_value = None
        self.identifiers = create_autospec(IdentifierProvider, instance=True)
        self.identifiers.generate.return_value = 'mentor-message'
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = self.now
        self.access = create_autospec(MentorAccessProvider, instance=True)
        self.attempt = MentorResponseAttempt(
            id='attempt',
            account_id='account',
            session_id='session',
            learner_message_id='learner-message',
            status=MentorResponseStatus.PROCESSING,
            context_hint=None,
            access_revision='revision',
            operation_key='operation',
            created_at=self.now,
            updated_at=self.now,
        )
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = self.attempt
        self.repositories.mentor_response_attempts.find_current.return_value = (
            self.attempt
        )
        self.repositories.mentor_response_attempts.transition.return_value = True
        self.repositories.mentor_response_events.next_sequence.return_value = 3
        self.repositories.mentor_response_events.snapshot.return_value = (
            MentorResponseSnapshot(
                attempt_id='attempt',
                learner_message_id='learner-message',
                status=MentorResponseStatus.PROCESSING,
                blocks=(
                    MentorResponseBlock(
                        block_key='approved', ordinal=0, intent=None, content='answer'
                    ),
                ),
                consultations=(),
                last_sequence=2,
                failure_code=None,
            )
        )
        self.subject = FinalizeMentorResponseUseCase(
            self.database, self.identifiers, self.clock, self.access
        )

    def test_should_persist_one_response_and_activity_under_session_lock(self) -> None:
        assert (
            self.subject.execute(
                'account', 'session', 'learner-message', 'answer', 'attempt', 'owner'
            )
            is True
        )

        self.repositories.mentor_sessions.find_by_id_for_update.assert_called_once_with(
            'account', 'session'
        )
        self.repositories.mentor_response_attempts.find_by_id_for_update.assert_called_once_with(
            'attempt'
        )
        self.repositories.mentor_response_attempts.find_current.assert_called_once_with(
            'account', 'session'
        )
        self.repositories.mentor_response_attempts.has_claim.assert_called_once_with(
            'attempt', 'owner', self.now
        )
        self.access.assert_current.assert_called_once_with(
            MentorAccessGrant(
                account_id='account',
                access_revision='revision',
                operation_key='operation',
            )
        )
        self.repositories.mentor_response_events.snapshot.assert_called_once_with(
            'account', 'session'
        )
        self.repositories.mentor_response_attempts.transition.assert_called_once_with(
            'attempt',
            MentorResponseStatus.PROCESSING,
            MentorResponseStatus.COMPLETED,
            'revision',
        )
        self.repositories.mentor_response_events.next_sequence.assert_called_once_with(
            'session'
        )
        self.repositories.mentor_response_events.append.assert_called_once_with(
            MentorResponseEvent(
                session_id='session',
                attempt_id='attempt',
                sequence=3,
                kind=MentorResponseEventKind.COMPLETED,
                status=MentorResponseStatus.COMPLETED,
                block=None,
                consultation=None,
                failure_code=None,
                created_at=self.now,
            )
        )
        persisted = self.repositories.mentor_messages.add.call_args.args[0]
        assert persisted.id == 'mentor-message'
        assert persisted.session_id == 'session'
        assert persisted.role is MentorMessageRole.MENTOR
        assert persisted.in_reply_to_message_id == 'learner-message'
        assert persisted.content == 'answer'
        assert persisted.created_at == self.now
        assert self.session.updated_at == self.now
        assert self.session.last_activity_at == self.now
        self.repositories.mentor_sessions.record_activity.assert_called_once_with(
            self.session
        )
        self.repositories.mentor_messages.find_by_id.assert_called_once_with(
            'account', 'session', 'learner-message'
        )
        self.repositories.mentor_messages.find_response.assert_called_once_with(
            'account', 'session', 'learner-message'
        )

    def test_should_treat_exact_response_replay_as_success(self) -> None:
        self.repositories.mentor_messages.find_response.return_value = MentorMessage(
            id='response',
            session_id='session',
            role=MentorMessageRole.MENTOR,
            content='answer',
            created_at=self.now,
            in_reply_to_message_id='learner-message',
        )

        assert (
            self.subject.execute(
                'account', 'session', 'learner-message', 'answer', 'attempt', 'owner'
            )
            is True
        )

        self.repositories.mentor_messages.add.assert_not_called()
        self.identifiers.generate.assert_not_called()
        self.repositories.mentor_sessions.record_activity.assert_not_called()
        assert self.session.updated_at == self.now
        assert self.session.last_activity_at == self.now

    def test_should_conflict_on_divergent_response_replay(self) -> None:
        self.repositories.mentor_messages.find_response.return_value = MentorMessage(
            id='response',
            session_id='session',
            role=MentorMessageRole.MENTOR,
            content='other',
            created_at=self.now,
            in_reply_to_message_id='learner-message',
        )

        with pytest.raises(MentorResponseConflictError):
            self.subject.execute(
                'account', 'session', 'learner-message', 'answer', 'attempt', 'owner'
            )

        self.repositories.mentor_messages.add.assert_not_called()
        self.identifiers.generate.assert_not_called()
        self.repositories.mentor_sessions.record_activity.assert_not_called()

    def test_should_return_false_when_learner_message_is_not_visible_to_account(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
            self.attempt, learner_message_id='foreign-message'
        )
        self.repositories.mentor_messages.find_by_id.return_value = None

        assert (
            self.subject.execute(
                'account', 'session', 'foreign-message', 'answer', 'attempt', 'owner'
            )
            is False
        )

        self.repositories.mentor_messages.find_by_id.assert_called_once_with(
            'account', 'session', 'foreign-message'
        )
        self.repositories.mentor_messages.find_response.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_sessions.record_activity.assert_not_called()

    def test_should_return_false_for_deleted_or_missing_targets(self) -> None:
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = None

        assert (
            self.subject.execute(
                'account', 'deleted', 'learner-message', 'answer', 'attempt', 'owner'
            )
            is False
        )

        self.repositories.mentor_messages.find_by_id.assert_not_called()

    def test_should_reject_non_learner_reply_target(self) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
            self.attempt, learner_message_id='mentor'
        )
        self.repositories.mentor_messages.find_by_id.return_value = MentorMessage(
            id='mentor',
            session_id='session',
            role=MentorMessageRole.MENTOR,
            content='old answer',
            created_at=self.now,
            in_reply_to_message_id='another',
        )

        with pytest.raises(MentorResponseConflictError):
            self.subject.execute(
                'account', 'session', 'mentor', 'answer', 'attempt', 'owner'
            )

        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_reject_content_not_in_approved_blocks(self) -> None:
        with pytest.raises(MentorResponseConflictError):
            self.subject.execute(
                'account',
                'session',
                'learner-message',
                'unreviewed candidate',
                'attempt',
                'owner',
            )
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_response_attempts.transition.assert_not_called()

    def test_should_not_complete_without_persisted_approved_blocks(self) -> None:
        self.repositories.mentor_response_events.snapshot.return_value = None
        assert (
            self.subject.execute(
                'account', 'session', 'learner-message', 'answer', 'attempt', 'owner'
            )
            is False
        )
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_refuse_expired_or_other_execution_owner(self) -> None:
        self.repositories.mentor_response_attempts.has_claim.return_value = False
        assert (
            self.subject.execute(
                'account',
                'session',
                'learner-message',
                'answer',
                'attempt',
                'expired-owner',
            )
            is False
        )
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_response_attempts.transition.assert_not_called()

    def test_should_refuse_processing_completion_without_execution_owner(self) -> None:
        assert (
            self.subject.execute(
                'account', 'session', 'learner-message', 'answer', 'attempt'
            )
            is False
        )
        self.repositories.mentor_messages.add.assert_not_called()

    @pytest.mark.parametrize(
        'field', ['account_id', 'session_id', 'learner_message_id']
    )
    def test_should_reject_each_attempt_ownership_mismatch(self, field: str) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
            self.attempt, **{field: 'foreign'}
        )
        assert (
            self.subject.execute(
                'account', 'session', 'learner-message', 'answer', 'attempt', 'owner'
            )
            is False
        )
        self.repositories.mentor_messages.find_by_id.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_response_attempts.transition.assert_not_called()

    def test_should_reject_superseded_attempt_even_when_owner_and_learner_match(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.find_current.return_value = replace(
            self.attempt, id='new-attempt'
        )
        assert (
            self.subject.execute(
                'account', 'session', 'learner-message', 'answer', 'attempt', 'owner'
            )
            is False
        )
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_response_attempts.transition.assert_not_called()

    def test_should_reject_approved_blocks_from_another_attempt(self) -> None:
        snapshot = self.repositories.mentor_response_events.snapshot.return_value
        self.repositories.mentor_response_events.snapshot.return_value = replace(
            snapshot, attempt_id='older-attempt'
        )
        assert (
            self.subject.execute(
                'account', 'session', 'learner-message', 'answer', 'attempt', 'owner'
            )
            is False
        )
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_response_attempts.transition.assert_not_called()

    @pytest.mark.parametrize('missing', ['attempt', 'current'])
    def test_should_reject_each_missing_attempt_record_without_completion_effects(
        self, missing: str
    ) -> None:
        if missing == 'attempt':
            self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = None
        else:
            self.repositories.mentor_response_attempts.find_current.return_value = None
        assert (
            self.subject.execute(
                'account', 'session', 'learner-message', 'answer', 'attempt', 'owner'
            )
            is False
        )
        self.access.assert_current.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_response_attempts.transition.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_sessions.record_activity.assert_not_called()

    def test_should_report_lost_completion_transition_without_reply_or_event(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.transition.return_value = False
        assert (
            self.subject.execute(
                'account', 'session', 'learner-message', 'answer', 'attempt', 'owner'
            )
            is False
        )
        self.repositories.mentor_response_attempts.transition.assert_called_once_with(
            'attempt',
            MentorResponseStatus.PROCESSING,
            MentorResponseStatus.COMPLETED,
            'revision',
        )
        self.identifiers.generate.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_sessions.record_activity.assert_not_called()

    def test_should_replay_completed_identical_reply_without_an_active_execution_lease(
        self,
    ) -> None:
        completed = replace(self.attempt, status=MentorResponseStatus.COMPLETED)
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = completed
        self.repositories.mentor_response_attempts.find_current.return_value = completed
        self.repositories.mentor_response_attempts.has_claim.return_value = False
        self.repositories.mentor_messages.find_response.return_value = MentorMessage(
            id='persisted-reply',
            session_id='session',
            role=MentorMessageRole.MENTOR,
            content='answer',
            created_at=self.now,
            in_reply_to_message_id='learner-message',
        )
        assert (
            self.subject.execute(
                'account', 'session', 'learner-message', 'answer', 'attempt'
            )
            is True
        )
        self.repositories.mentor_response_attempts.has_claim.assert_not_called()
        self.repositories.mentor_response_attempts.transition.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_sessions.record_activity.assert_not_called()
        self.identifiers.generate.assert_not_called()

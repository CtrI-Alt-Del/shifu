from datetime import UTC, datetime
from typing import cast
from unittest.mock import call, create_autospec

import pytest

from shifu.intelligence.core.domain.entities import MentorMessage, MentorSession
from shifu.intelligence.core.domain.enums import MentorMessageRole
from shifu.intelligence.core.domain.errors import (
    MentorInputInvalidError,
    MentorSessionNotFoundError,
    MentorSubmissionConflictError,
    MentorTitleUnavailableError,
)
from shifu.intelligence.core.domain.structures import (
    MentorMessagesPage,
    MentorSubmissionRecord,
)
from shifu.intelligence.core.interfaces import (
    GenerateMentorTitleWorkflow,
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.use_cases import CreateMentorSessionUseCase
from shifu.intelligence.providers.openrouter import (
    UnavailableGenerateMentorTitleWorkflow,
)
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class TestCreateMentorSessionUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.identifiers = create_autospec(IdentifierProvider, instance=True)
        self.identifiers.generate.side_effect = [
            '01JMENTORSESSION000000000001',
            '01JMENTORMESSAGE000000000001',
        ]
        self.clock = create_autospec(ClockProvider, instance=True)
        self.now = datetime(2026, 1, 1, tzinfo=UTC)
        self.clock.now.return_value = self.now
        self.workflow = create_autospec(GenerateMentorTitleWorkflow, instance=True)
        self.workflow.generate.return_value = 'Título inferido'
        self.subject = CreateMentorSessionUseCase(
            self.database, self.identifiers, self.clock, self.workflow
        )

    def test_should_atomically_persist_exact_first_message_and_final_title(
        self,
    ) -> None:
        self.repositories.mentor_sessions.find_submission.side_effect = [None, None]

        result = self.subject.execute(
            '01JACCOUNT000000000000000001',
            '123e4567-e89b-42d3-a456-426614174000',
            '  Olá\n\t mundo  ',
        )

        self.workflow.generate.assert_called_once_with('  Olá\n\t mundo  ')
        assert result.created is True
        assert result.detail.session.title == 'Título inferido'
        assert (
            result.detail.pending_learner_message_id == '01JMENTORMESSAGE000000000001'
        )
        assert result.detail.messages.items[0] == MentorMessage(
            id='01JMENTORMESSAGE000000000001',
            session_id='01JMENTORSESSION000000000001',
            role=MentorMessageRole.LEARNER,
            content='  Olá\n\t mundo  ',
            created_at=self.now,
            in_reply_to_message_id=None,
        )
        persisted_message = cast(
            'MentorMessage', self.repositories.mentor_messages.add.call_args.args[0]
        )
        assert persisted_message.id == '01JMENTORMESSAGE000000000001'
        assert persisted_message.session_id == '01JMENTORSESSION000000000001'
        assert persisted_message.role is MentorMessageRole.LEARNER
        assert persisted_message.content == '  Olá\n\t mundo  '
        assert persisted_message.created_at == self.now
        assert persisted_message.in_reply_to_message_id is None
        persisted = cast(
            'MentorSession', self.repositories.mentor_sessions.add.call_args.args[0]
        )
        assert persisted.account_id == '01JACCOUNT000000000000000001'
        assert persisted.created_at == self.now
        assert persisted.updated_at == self.now
        assert persisted.last_activity_at == self.now
        self.repositories.mentor_sessions.add.assert_called_once_with(
            persisted,
            '123e4567-e89b-42d3-a456-426614174000',
            '6cc2e06c0a012fbab4006311f0e60598cf4f3e097c1f8411a878c9f5e45bc6c5',
        )
        self.repositories.mentor_messages.add.assert_called_once()
        assert self.database.transaction.call_count == 2
        assert self.repositories.mentor_sessions.lock_submission.call_count == 1

    def test_should_limit_title_input_to_first_1000_codepoints(self) -> None:
        self.repositories.mentor_sessions.find_submission.side_effect = [None, None]
        message = '🙂' * 1001

        self.subject.execute(
            '01JACCOUNT000000000000000001',
            '123e4567-e89b-42d3-a456-426614174000',
            message,
        )

        self.workflow.generate.assert_called_once_with('🙂' * 1000)
        persisted = cast(
            'MentorMessage', self.repositories.mentor_messages.add.call_args.args[0]
        )
        assert persisted.content == message

    def test_should_fallback_to_normalized_prefix_when_title_generation_is_unavailable(
        self,
    ) -> None:
        self.repositories.mentor_sessions.find_submission.side_effect = [None, None]
        self.workflow.generate.side_effect = MentorTitleUnavailableError()

        result = self.subject.execute(
            '01JACCOUNT000000000000000001',
            '123e4567-e89b-42d3-a456-426614174000',
            '  café\n com   espaços  ',
        )

        assert result.detail.session.title == 'café com espaços'

    @pytest.mark.parametrize(
        ('generated_title', 'expected_title'),
        [
            ('', 'mensagem original'),
            ('x' * 120, 'x' * 120),
            ('x' * 121, 'mensagem original'),
        ],
    )
    def test_should_validate_generated_title_length_boundaries(
        self, generated_title: str, expected_title: str
    ) -> None:
        self.repositories.mentor_sessions.find_submission.side_effect = [None, None]
        self.workflow.generate.return_value = generated_title

        result = self.subject.execute(
            '01JACCOUNT000000000000000001',
            '123e4567-e89b-42d3-a456-426614174000',
            'mensagem original',
        )

        assert result.detail.session.title == expected_title

    @pytest.mark.parametrize(
        ('message', 'expected_title'),
        [
            ('x' * 119 + ' y', 'x' * 119),
            ('x' * 120 + 'y', 'x' * 120),
        ],
    )
    def test_should_trim_fallback_at_the_120_character_boundary(
        self, message: str, expected_title: str
    ) -> None:
        self.repositories.mentor_sessions.find_submission.side_effect = [None, None]
        self.workflow.generate.side_effect = MentorTitleUnavailableError()

        result = self.subject.execute(
            '01JACCOUNT000000000000000001',
            '123e4567-e89b-42d3-a456-426614174000',
            message,
        )

        assert result.detail.session.title == expected_title

    def test_should_fallback_when_title_provider_is_not_configured(self) -> None:
        self.repositories.mentor_sessions.find_submission.side_effect = [None, None]
        subject = CreateMentorSessionUseCase(
            self.database,
            self.identifiers,
            self.clock,
            UnavailableGenerateMentorTitleWorkflow(),
        )

        result = subject.execute(
            '01JACCOUNT000000000000000001',
            '123e4567-e89b-42d3-a456-426614174000',
            '  dúvida   sem título  ',
        )

        assert result.created is True
        assert result.detail.session.title == 'dúvida sem título'

    def test_should_return_matching_replay_without_inference_or_new_writes(
        self,
    ) -> None:
        record = MentorSubmissionRecord(
            session_id='01JMENTORSESSION000000000001',
            content_fingerprint='2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824',
            deleted_at=None,
        )
        session = MentorSession(
            id=record.session_id,
            account_id='01JACCOUNT000000000000000001',
            title='Renomeado',
            created_at=self.now,
            updated_at=self.now,
            last_activity_at=self.now,
        )
        self.repositories.mentor_sessions.find_submission.return_value = record
        self.repositories.mentor_sessions.find_by_id.return_value = session
        messages = MentorMessagesPage(
            items=[
                MentorMessage(
                    id='01JMENTORMESSAGE000000000001',
                    session_id=record.session_id,
                    role=MentorMessageRole.LEARNER,
                    content='hello',
                    created_at=self.now,
                    in_reply_to_message_id=None,
                )
            ],
            next_cursor=None,
        )
        self.repositories.mentor_messages.find_many.return_value = messages
        self.repositories.mentor_messages.find_pending_learner_message_id.return_value = '01JMENTORMESSAGE000000000001'

        result = self.subject.execute(
            '01JACCOUNT000000000000000001',
            '123e4567-e89b-42d3-a456-426614174000',
            'hello',
        )

        assert result.created is False
        assert result.detail.session.title == 'Renomeado'
        assert result.detail.messages == messages
        assert result.detail.pending_learner_message_id == (
            '01JMENTORMESSAGE000000000001'
        )
        self.repositories.mentor_sessions.find_submission.assert_has_calls(
            [
                call(
                    '01JACCOUNT000000000000000001',
                    '123e4567-e89b-42d3-a456-426614174000',
                ),
                call(
                    '01JACCOUNT000000000000000001',
                    '123e4567-e89b-42d3-a456-426614174000',
                ),
            ]
        )
        assert self.repositories.mentor_sessions.find_submission.call_count == 2
        self.repositories.mentor_messages.find_many.assert_called_once_with(
            '01JACCOUNT000000000000000001', record.session_id, None
        )
        self.repositories.mentor_messages.find_pending_learner_message_id.assert_called_once_with(
            '01JACCOUNT000000000000000001', record.session_id
        )
        self.workflow.generate.assert_not_called()
        self.repositories.mentor_sessions.add.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_return_replay_found_after_lock_without_creating_a_second_session(
        self,
    ) -> None:
        record = MentorSubmissionRecord(
            session_id='01JMENTORSESSION000000000001',
            content_fingerprint='2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824',
            deleted_at=None,
        )
        session = MentorSession(
            id=record.session_id,
            account_id='01JACCOUNT000000000000000001',
            title='Criada por requisição concorrente',
            created_at=self.now,
            updated_at=self.now,
            last_activity_at=self.now,
        )
        self.repositories.mentor_sessions.find_submission.side_effect = [
            None,
            record,
            record,
        ]
        self.repositories.mentor_sessions.find_by_id.return_value = session

        result = self.subject.execute(
            '01JACCOUNT000000000000000001',
            '123e4567-e89b-42d3-a456-426614174000',
            'hello',
        )

        assert result.created is False
        assert result.detail.session.title == 'Criada por requisição concorrente'
        self.repositories.mentor_sessions.lock_submission.assert_called_once_with(
            '01JACCOUNT000000000000000001',
            '123e4567-e89b-42d3-a456-426614174000',
        )
        self.repositories.mentor_sessions.lock_session.assert_called_once_with(
            '01JACCOUNT000000000000000001', '01JMENTORSESSION000000000001'
        )
        self.repositories.mentor_sessions.find_submission.assert_has_calls(
            [
                call(
                    '01JACCOUNT000000000000000001',
                    '123e4567-e89b-42d3-a456-426614174000',
                ),
                call(
                    '01JACCOUNT000000000000000001',
                    '123e4567-e89b-42d3-a456-426614174000',
                ),
                call(
                    '01JACCOUNT000000000000000001',
                    '123e4567-e89b-42d3-a456-426614174000',
                ),
            ]
        )
        self.repositories.mentor_sessions.add.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_not_replay_a_submission_when_its_session_is_not_owned_or_visible(
        self,
    ) -> None:
        self.repositories.mentor_sessions.find_submission.return_value = MentorSubmissionRecord(
            session_id='01JMENTORSESSION000000000001',
            content_fingerprint='2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824',
            deleted_at=None,
        )
        self.repositories.mentor_sessions.find_by_id.return_value = None

        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute(
                '01JACCOUNT000000000000000001',
                '123e4567-e89b-42d3-a456-426614174000',
                'hello',
            )

        self.repositories.mentor_sessions.find_by_id.assert_called_once_with(
            '01JACCOUNT000000000000000001', '01JMENTORSESSION000000000001'
        )
        self.repositories.mentor_sessions.add.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()
        self.workflow.generate.assert_not_called()

    def test_should_reject_changed_content_under_a_replayed_key(self) -> None:
        self.repositories.mentor_sessions.find_submission.return_value = (
            MentorSubmissionRecord(
                session_id='01JMENTORSESSION000000000001',
                content_fingerprint='other',
                deleted_at=None,
            )
        )

        with pytest.raises(MentorSubmissionConflictError):
            self.subject.execute(
                '01JACCOUNT000000000000000001',
                '123e4567-e89b-42d3-a456-426614174000',
                'hello',
            )

        self.workflow.generate.assert_not_called()
        self.repositories.mentor_sessions.add.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_not_recreate_deleted_submission_key(self) -> None:
        self.repositories.mentor_sessions.find_submission.return_value = (
            MentorSubmissionRecord(
                session_id='01JMENTORSESSION000000000001',
                content_fingerprint=None,
                deleted_at=self.now,
            )
        )

        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute(
                '01JACCOUNT000000000000000001',
                '123e4567-e89b-42d3-a456-426614174000',
                'hello',
            )

        self.workflow.generate.assert_not_called()
        self.repositories.mentor_sessions.add.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_revalidate_submission_after_waiting_for_session_lock(self) -> None:
        active = MentorSubmissionRecord(
            session_id='01JMENTORSESSION000000000001',
            content_fingerprint=(
                '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
            ),
            deleted_at=None,
        )
        tombstone = MentorSubmissionRecord(
            session_id=active.session_id,
            content_fingerprint=None,
            deleted_at=self.now,
        )
        self.repositories.mentor_sessions.find_submission.side_effect = [
            active,
            tombstone,
        ]

        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute(
                '01JACCOUNT000000000000000001',
                '123e4567-e89b-42d3-a456-426614174000',
                'hello',
            )

        self.repositories.mentor_sessions.lock_session.assert_called_once_with(
            '01JACCOUNT000000000000000001', active.session_id
        )
        self.repositories.mentor_sessions.find_by_id.assert_not_called()
        self.repositories.mentor_sessions.add.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_reject_missing_submission_after_waiting_for_session_lock(
        self,
    ) -> None:
        active = MentorSubmissionRecord(
            session_id='01JMENTORSESSION000000000001',
            content_fingerprint=(
                '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
            ),
            deleted_at=None,
        )
        self.repositories.mentor_sessions.find_submission.side_effect = [active, None]

        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute(
                '01JACCOUNT000000000000000001',
                '123e4567-e89b-42d3-a456-426614174000',
                'hello',
            )

        self.repositories.mentor_sessions.lock_session.assert_called_once_with(
            '01JACCOUNT000000000000000001', active.session_id
        )
        self.repositories.mentor_sessions.find_by_id.assert_not_called()
        self.repositories.mentor_sessions.add.assert_not_called()

    @pytest.mark.parametrize('message', ['', '  \n\t '])
    def test_should_reject_empty_or_whitespace_first_message(
        self, message: str
    ) -> None:
        with pytest.raises(MentorInputInvalidError):
            self.subject.execute(
                '01JACCOUNT000000000000000001',
                '123e4567-e89b-42d3-a456-426614174000',
                message,
            )

        self.database.transaction.assert_not_called()
        self.workflow.generate.assert_not_called()

    def test_should_reject_non_uuidv4_submission_key(self) -> None:
        with pytest.raises(MentorInputInvalidError):
            self.subject.execute(
                'account', '123e4567-e89b-12d3-a456-426614174000', 'ok'
            )

        self.database.transaction.assert_not_called()

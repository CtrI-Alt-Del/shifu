import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta
from unittest.mock import create_autospec

import pytest

from shifu.fakers.intelligence.entities import LearnerMemoryFaker
from shifu.intelligence.core.domain.entities import (
    LearnerMemory,
    LearnerMemoryChange,
    MentorResponseAttempt,
)
from shifu.intelligence.core.domain.enums import (
    LearnerMemoryCategory,
    LearnerMemoryChangeKind,
    MentorMessageRole,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import (
    LearnerMemoryAnalysis,
    LearnerMemoryConcept,
    LearnerMemoryOrigin,
    LearnerMemoryStatement,
)
from shifu.intelligence.core.interfaces import (
    LearnerMemoryAnalyzerProvider,
    LearnerMemorySimilarityProvider,
)
from shifu.intelligence.core.use_cases.update_learner_memories_use_case import (
    UpdateLearnerMemoriesUseCase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from tests.intelligence.core.use_cases.mentor_response_test_setup import (
    MentorResponseTestSetup,
)

_PREFERENCE = LearnerMemoryCategory.EXPLANATION_PREFERENCE
_KNOWLEDGE = LearnerMemoryCategory.DECLARED_KNOWLEDGE
_PYTHON = LearnerMemoryConcept(key='python', label='Python')
_THRESHOLD = 0.4


def _statement(
    content: str = 'Prefiro exemplos em Python.',
    category: LearnerMemoryCategory = _PREFERENCE,
) -> LearnerMemoryStatement:
    return LearnerMemoryStatement(
        category=category, content=content, concepts=(_PYTHON,)
    )


def _analysis(
    *statements: LearnerMemoryStatement, sentences: int | None = None
) -> LearnerMemoryAnalysis:
    return LearnerMemoryAnalysis(
        statements=statements,
        sentence_count=len(statements) if sentences is None else sentences,
    )


class TestUpdateLearnerMemoriesUseCase(MentorResponseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare(MentorResponseStatus.PROCESSING)
        self.analyzer = create_autospec(LearnerMemoryAnalyzerProvider, instance=True)
        self.similarity = create_autospec(
            LearnerMemorySimilarityProvider, instance=True
        )
        self.subject = UpdateLearnerMemoriesUseCase(
            self.database,
            self.analyzer,
            self.similarity,
            self.access,
            self.clock,
            self.identifiers,
            _THRESHOLD,
        )
        self.memories = self.repositories.learner_memories
        self.changes = self.repositories.learner_memory_changes
        self.messages = self.repositories.mentor_messages
        self.messages.find_memory_analysis.return_value = None
        self.memories.lock_account.return_value = None
        self.memories.find_many_by_account.return_value = ()
        self.similarity.similarity.return_value = 0.0
        self.analyzer.analyze.return_value = _analysis(_statement())
        self.identifiers.generate.side_effect = [f'id-{n}' for n in range(1, 20)]
        self.order: list[str] = []
        self.analyzer.analyze.side_effect = self._analyze
        self.repositories.mentor_sessions.lock_session.side_effect = self._record(
            'lock_session'
        )
        self.repositories.mentor_response_attempts.find_current.side_effect = (
            self._current
        )
        self.access.assert_current.side_effect = self._record('access')
        self.memories.lock_account.side_effect = self._lock_account
        self.memories.add.side_effect = self._record('add')
        self.memories.update.side_effect = self._record('update')
        self.memories.add_origin.side_effect = self._record('add_origin')
        self.changes.add.side_effect = self._record('change')
        self.messages.mark_memory_analyzed.side_effect = self._record('receipt')
        self.fence: datetime | None = None
        self.next_analysis: LearnerMemoryAnalysis | Exception = _analysis(_statement())

    # --- helpers --------------------------------------------------------------

    def _record(self, name: str) -> Callable[..., None]:
        def record(*_args: object, **_kwargs: object) -> None:
            self.order.append(name)

        return record

    def _current(self, *_args: object) -> MentorResponseAttempt:
        self.order.append('current')
        return self.attempt

    def _analyze(self, _text: str) -> LearnerMemoryAnalysis:
        self.order.append('analyze')
        if isinstance(self.next_analysis, Exception):
            raise self.next_analysis
        return self.next_analysis

    def _lock_account(self, _account_id: str) -> datetime | None:
        self.order.append('lock_account')
        return self.fence

    def _settle_order(self) -> list[str]:
        return self.order[self.order.index('analyze') + 1 :]

    def _existing(
        self,
        *,
        category: LearnerMemoryCategory = _PREFERENCE,
        content: str = 'Prefiro exemplos em JavaScript.',
        last_declared_at: datetime | None = None,
    ) -> LearnerMemory:
        memory = LearnerMemoryFaker.fake(
            id='memory-old',
            account_id='account',
            category=category,
            content=content,
            last_declared_at=last_declared_at or self.now - timedelta(days=1),
            created_at=self.now - timedelta(days=2),
            updated_at=self.now - timedelta(days=1),
        )
        self.memories.find_many_by_account.return_value = (memory,)
        return memory

    def _assert_nothing_written(self) -> None:
        self.memories.add.assert_not_called()
        self.memories.update.assert_not_called()
        self.memories.add_origin.assert_not_called()
        self.changes.add.assert_not_called()
        self.messages.mark_memory_analyzed.assert_not_called()

    # --- creation, receipt and policy -----------------------------------------

    def test_should_skip_a_message_that_already_has_an_analysis_receipt(self) -> None:
        self.messages.find_memory_analysis.return_value = (self.now, True)

        self.subject.execute('attempt', 'owner')

        self.analyzer.analyze.assert_not_called()
        self._assert_nothing_written()
        self.memories.lock_account.assert_not_called()

    def test_should_create_a_memory_with_origin_change_record_and_receipt(self) -> None:
        self.subject.execute('attempt', 'owner')

        self.analyzer.analyze.assert_called_once_with(self.message.content)
        memory = self.memories.add.call_args.args[0]
        assert memory.id == 'id-1'
        assert memory.account_id == 'account'
        assert memory.category is _PREFERENCE
        assert memory.content == 'Prefiro exemplos em Python.'
        assert memory.version == 1
        assert memory.last_declared_at == self.message.created_at
        assert self.memories.add.call_args.args[1] == (_PYTHON,)
        assert self.memories.add.call_args.args[2] == LearnerMemoryOrigin(
            session_id='session',
            message_id='message',
            declared_at=self.message.created_at,
        )
        self.changes.add.assert_called_once_with(
            LearnerMemoryChange(
                id='id-2',
                account_id='account',
                memory_id='id-1',
                session_id='session',
                message_id='message',
                kind=LearnerMemoryChangeKind.CREATED,
                category=_PREFERENCE,
                content='Prefiro exemplos em Python.',
                previous_content=None,
                created_at=self.now,
            )
        )
        self.messages.mark_memory_analyzed.assert_called_once_with(
            'message', self.now, statement_only=True
        )
        self.memories.update.assert_not_called()

    def test_should_read_only_the_typed_text_of_the_learner_message(self) -> None:
        self.subject.execute('attempt', 'owner')

        self.analyzer.analyze.assert_called_once_with('  pergunta exata  ')
        self.messages.find_by_id.assert_called_with('account', 'session', 'message')
        self.repositories.mentor_attachments.find_by_message_id.assert_not_called()
        self.repositories.mentor_session_summaries.find_ready.assert_not_called()
        self.messages.find_all.assert_not_called()

    def test_should_lock_session_then_check_fences_then_lock_the_account(self) -> None:
        self.subject.execute('attempt', 'owner')

        assert self._settle_order() == [
            'lock_session',
            'current',
            'access',
            'lock_account',
            'add',
            'change',
            'receipt',
        ]

    def test_should_write_a_receipt_without_touching_memories_when_nothing_is_a_statement(
        self,
    ) -> None:
        self.next_analysis = _analysis(sentences=2)

        self.subject.execute('attempt', 'owner')

        self.messages.mark_memory_analyzed.assert_called_once_with(
            'message', self.now, statement_only=False
        )
        self.memories.lock_account.assert_not_called()
        self.memories.add.assert_not_called()
        self.changes.add.assert_not_called()

    def test_should_not_mark_a_message_with_a_question_as_statement_only(self) -> None:
        # "Prefiro X. Como funciona Y?": two sentences, one statement.
        self.next_analysis = _analysis(_statement(), sentences=2)

        self.subject.execute('attempt', 'owner')

        self.memories.add.assert_called_once()
        self.messages.mark_memory_analyzed.assert_called_once_with(
            'message', self.now, statement_only=False
        )

    def test_should_record_no_usage_progress_or_event(self) -> None:
        self.subject.execute('attempt', 'owner')

        self.repositories.events.add.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()
        self.access.authorize.assert_not_called()

    # --- create versus update --------------------------------------------------

    @pytest.mark.parametrize(
        ('score', 'updates'),
        [(_THRESHOLD - 0.001, False), (_THRESHOLD, True), (0.95, True)],
    )
    def test_should_update_only_when_similarity_reaches_the_threshold(
        self, score: float, updates: bool
    ) -> None:
        memory = self._existing()
        self.similarity.similarity.return_value = score
        self.next_analysis = _analysis(_statement('Prefiro exemplos em Python.'))

        self.subject.execute('attempt', 'owner')

        self.similarity.similarity.assert_called_once_with(
            'Prefiro exemplos em Python.', 'Prefiro exemplos em JavaScript.'
        )
        if updates:
            self.memories.add.assert_not_called()
            self.memories.update.assert_called_once_with(memory, (_PYTHON,))
        else:
            self.memories.update.assert_not_called()
            self.memories.add.assert_called_once()

    def test_should_update_content_version_origin_and_keep_the_previous_text(
        self,
    ) -> None:
        memory = self._existing()
        self.similarity.similarity.return_value = 0.5
        self.next_analysis = _analysis(_statement('Prefiro exemplos em Python.'))

        self.subject.execute('attempt', 'owner')

        assert memory.content == 'Prefiro exemplos em Python.'
        assert memory.version == 2
        assert memory.last_declared_at == self.message.created_at
        assert memory.updated_at == self.now
        self.memories.add_origin.assert_called_once_with(
            'memory-old',
            LearnerMemoryOrigin(
                session_id='session',
                message_id='message',
                declared_at=self.message.created_at,
            ),
        )
        self.changes.add.assert_called_once_with(
            LearnerMemoryChange(
                id='id-1',
                account_id='account',
                memory_id='memory-old',
                session_id='session',
                message_id='message',
                kind=LearnerMemoryChangeKind.UPDATED,
                category=_PREFERENCE,
                content='Prefiro exemplos em Python.',
                previous_content='Prefiro exemplos em JavaScript.',
                created_at=self.now,
            )
        )
        self.messages.mark_memory_analyzed.assert_called_once_with(
            'message', self.now, statement_only=True
        )

    def test_should_compare_only_memories_of_the_same_category(self) -> None:
        self._existing(category=_KNOWLEDGE, content='Sei Python.')
        self.similarity.similarity.return_value = 1.0

        self.subject.execute('attempt', 'owner')

        self.similarity.similarity.assert_not_called()
        self.memories.update.assert_not_called()
        self.memories.add.assert_called_once()

    def test_should_update_the_most_similar_memory_of_the_category(self) -> None:
        first = LearnerMemoryFaker.fake(
            id='first',
            account_id='account',
            category=_PREFERENCE,
            content='Prefiro respostas curtas.',
            last_declared_at=self.now - timedelta(days=3),
        )
        second = LearnerMemoryFaker.fake(
            id='second',
            account_id='account',
            category=_PREFERENCE,
            content='Prefiro exemplos em JavaScript.',
            last_declared_at=self.now - timedelta(days=2),
        )
        self.memories.find_many_by_account.return_value = (first, second)

        def score(_new: str, old: str) -> float:
            return 0.9 if 'JavaScript' in old else 0.6

        self.similarity.similarity.side_effect = score

        self.subject.execute('attempt', 'owner')

        self.memories.update.assert_called_once_with(second, (_PYTHON,))
        assert first.version == 1

    def test_should_discard_a_declaration_that_is_not_newer_than_the_memory(
        self,
    ) -> None:
        memory = self._existing(
            last_declared_at=self.message.created_at, content='Prefiro curtas.'
        )
        self.similarity.similarity.return_value = 0.9

        self.subject.execute('attempt', 'owner')

        assert memory.content == 'Prefiro curtas.'
        assert memory.version == 1
        self.memories.add.assert_not_called()
        self.memories.update.assert_not_called()
        self.memories.add_origin.assert_not_called()
        self.changes.add.assert_not_called()
        self.messages.mark_memory_analyzed.assert_called_once_with(
            'message', self.now, statement_only=False
        )

    def test_should_discard_a_late_message_older_than_a_later_edit(self) -> None:
        memory = self._existing(last_declared_at=self.now + timedelta(minutes=5))
        self.similarity.similarity.return_value = 0.9

        self.subject.execute('attempt', 'owner')

        assert memory.version == 1
        self.memories.update.assert_not_called()
        self.changes.add.assert_not_called()
        self.messages.mark_memory_analyzed.assert_called_once_with(
            'message', self.now, statement_only=False
        )

    def test_should_not_duplicate_two_similar_statements_of_one_message(self) -> None:
        self.next_analysis = _analysis(
            _statement('Prefiro exemplos curtos.'),
            _statement('Prefiro exemplos em Python.'),
        )
        self.similarity.similarity.return_value = 0.9

        self.subject.execute('attempt', 'owner')

        self.memories.add.assert_called_once()
        self.memories.update.assert_not_called()
        self.changes.add.assert_called_once()
        self.messages.mark_memory_analyzed.assert_called_once_with(
            'message', self.now, statement_only=False
        )

    def test_should_create_one_memory_per_distinct_statement(self) -> None:
        self.next_analysis = _analysis(
            _statement('Prefiro exemplos curtos.'),
            _statement('Sei Python.', _KNOWLEDGE),
        )

        self.subject.execute('attempt', 'owner')

        assert self.memories.add.call_count == 2
        assert [call.args[0].id for call in self.changes.add.call_args_list] == [
            'id-2',
            'id-4',
        ]
        assert [call.args[0].memory_id for call in self.changes.add.call_args_list] == [
            'id-1',
            'id-3',
        ]
        self.messages.mark_memory_analyzed.assert_called_once_with(
            'message', self.now, statement_only=True
        )

    # --- deletion fence ---------------------------------------------------------

    @pytest.mark.parametrize(
        ('offset', 'accepted'),
        [
            (None, True),
            (timedelta(seconds=-1), True),
            (timedelta(seconds=0), False),
            (timedelta(seconds=1), False),
        ],
    )
    def test_should_drop_statements_created_at_or_before_the_deletion_fence(
        self, offset: timedelta | None, accepted: bool
    ) -> None:
        self.fence = None if offset is None else self.message.created_at + offset

        self.subject.execute('attempt', 'owner')

        assert self.memories.add.called is accepted
        assert self.changes.add.called is accepted
        self.messages.mark_memory_analyzed.assert_called_once_with(
            'message', self.now, statement_only=accepted
        )

    def test_should_not_update_a_memory_from_a_message_before_the_fence(self) -> None:
        self._existing()
        self.similarity.similarity.return_value = 0.9
        self.fence = self.message.created_at

        self.subject.execute('attempt', 'owner')

        self.memories.update.assert_not_called()
        self.memories.add.assert_not_called()
        self.messages.mark_memory_analyzed.assert_called_once_with(
            'message', self.now, statement_only=False
        )

    # --- failures ----------------------------------------------------------------

    @pytest.mark.parametrize(
        'cause', ['tombstoned', 'cancelled', 'superseded', 'access']
    )
    def test_should_write_nothing_when_a_fence_fails_before_the_commit(
        self, cause: str
    ) -> None:
        def lose_the_fence(_text: str) -> LearnerMemoryAnalysis:
            self.order.append('analyze')
            if cause == 'tombstoned':
                self.repositories.mentor_sessions.find_by_id_for_update.return_value = (
                    None
                )
            elif cause == 'cancelled':
                self.repositories.mentor_response_attempts.find_by_id.return_value = (
                    replace(self.attempt, status=MentorResponseStatus.CANCELLED)
                )
            elif cause == 'superseded':
                self.repositories.mentor_response_attempts.find_current.side_effect = (
                    None
                )
                self.repositories.mentor_response_attempts.find_current.return_value = (
                    replace(self.attempt, id='newer')
                )
            else:
                self.access.assert_current.side_effect = ServiceUnavailableError()
            return _analysis(_statement())

        self.analyzer.analyze.side_effect = lose_the_fence

        self.subject.execute('attempt', 'owner')

        self.memories.lock_account.assert_not_called()
        self._assert_nothing_written()

    def test_should_write_nothing_when_the_claim_is_lost_before_the_commit(
        self,
    ) -> None:
        def lose_the_claim(_text: str) -> LearnerMemoryAnalysis:
            self.order.append('analyze')
            self.repositories.mentor_response_attempts.has_claim.return_value = False
            return _analysis(_statement())

        self.analyzer.analyze.side_effect = lose_the_claim

        self.subject.execute('attempt', 'owner')

        self.memories.lock_account.assert_not_called()
        self._assert_nothing_written()

    def test_should_not_analyze_when_access_is_revoked_before_the_step(self) -> None:
        self.access.assert_current.side_effect = ServiceUnavailableError()

        self.subject.execute('attempt', 'owner')

        self.analyzer.analyze.assert_not_called()
        self._assert_nothing_written()

    @pytest.mark.parametrize('cause', ['missing', 'mentor', 'attempt'])
    def test_should_do_nothing_without_a_claimable_learner_message(
        self, cause: str
    ) -> None:
        if cause == 'missing':
            self.messages.find_by_id.return_value = None
        elif cause == 'mentor':
            self.messages.find_by_id.return_value = replace(
                self.message, role=MentorMessageRole.MENTOR
            )
        else:
            self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = None

        self.subject.execute('attempt', 'owner')

        self.analyzer.analyze.assert_not_called()
        self._assert_nothing_written()

    def test_should_not_raise_nor_write_when_the_analyzer_fails(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        self.next_analysis = RuntimeError('texto privado do aprendiz')

        with caplog.at_level(logging.DEBUG):
            self.subject.execute('attempt', 'owner')

        self._assert_nothing_written()
        self.memories.lock_account.assert_not_called()
        assert 'analysis_failed' in caplog.text
        assert 'texto privado' not in caplog.text
        assert 'pergunta exata' not in caplog.text

    def test_should_write_no_receipt_when_a_statement_write_fails(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        self.memories.add.side_effect = RuntimeError('Prefiro exemplos em Python.')

        with caplog.at_level(logging.DEBUG):
            self.subject.execute('attempt', 'owner')

        self.messages.mark_memory_analyzed.assert_not_called()
        self.changes.add.assert_not_called()
        assert 'commit_rejected' in caplog.text
        assert 'Prefiro' not in caplog.text

    def test_should_not_raise_when_the_database_fails(self) -> None:
        self.database.transaction.side_effect = RuntimeError('database')

        self.subject.execute('attempt', 'owner')

        self.analyzer.analyze.assert_not_called()

    def test_should_log_only_counts_after_a_successful_analysis(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.DEBUG):
            self.subject.execute('attempt', 'owner')

        assert 'created=1' in caplog.text
        assert 'Python' not in caplog.text
        assert 'pergunta exata' not in caplog.text

    def test_should_retry_analysis_after_a_failed_attempt(self) -> None:
        self.next_analysis = RuntimeError('boom')
        self.subject.execute('attempt', 'owner')
        self.messages.mark_memory_analyzed.assert_not_called()

        self.next_analysis = _analysis(_statement())
        self.subject.execute('attempt', 'owner')

        assert self.analyzer.analyze.call_count == 2
        self.messages.mark_memory_analyzed.assert_called_once_with(
            'message', self.now, statement_only=True
        )

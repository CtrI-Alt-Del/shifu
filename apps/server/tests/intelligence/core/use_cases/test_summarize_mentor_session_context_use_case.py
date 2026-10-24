from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import create_autospec

import pytest
from shifu.intelligence.core.domain.entities import (
    MentorMessage,
    MentorSession,
    MentorSessionSummary,
)
from shifu.intelligence.core.domain.enums import (
    MentorMessageRole,
    MentorResponseEventKind,
    MentorResponseStatus,
    MentorSummaryExcerptKind,
    MentorSummaryFailureCode,
    MentorSummaryStatus,
    MentorWorkflowStep,
)
from shifu.intelligence.core.domain.structures import (
    MentorConversationSummaryContext,
    MentorConversationSummaryDraft,
    MentorMessageVolume,
    MentorSummaryBoundary,
    MentorSummaryExcerptSpan,
)
from shifu.intelligence.core.interfaces import (
    MentorConversationSummarizerProvider,
    MentorTelemetryProvider,
)
from shifu.intelligence.core.use_cases import (
    RecordMentorResponseProgressUseCase,
    RenewMentorResponseClaimUseCase,
    SummarizeMentorSessionContextUseCase,
)
from shifu.shared.core.domain.errors import (
    AuthorizationError,
    ConflictError,
    ServiceUnavailableError,
)
from sqlalchemy.exc import OperationalError
from tests.intelligence.core.use_cases.mentor_response_test_setup import (
    MentorResponseTestSetup,
)

_THRESHOLD_CASES = [
    pytest.param(19, 15_999, False, id='below-both'),
    pytest.param(20, 0, True, id='twenty-messages'),
    pytest.param(19, 16_000, True, id='sixteen-thousand-code-points'),
    pytest.param(1, 16_000, True, id='single-huge-message'),
    pytest.param(0, 0, False, id='nothing-to-summarize'),
]


def _message(index: int, content: str | None = None) -> MentorMessage:
    learner = index % 2 == 1
    return MentorMessage(
        id=f'm{index:02d}',
        session_id='session',
        role=MentorMessageRole.LEARNER if learner else MentorMessageRole.MENTOR,
        content=content or f'Mensagem {index} sobre range e listas em Python.',
        created_at=datetime(2026, 10, 10, tzinfo=UTC) + timedelta(minutes=index),
        in_reply_to_message_id=None if learner else f'm{index - 1:02d}',
    )


def _span(
    message_id: str, start: int, end: int, kind: MentorSummaryExcerptKind
) -> MentorSummaryExcerptSpan:
    return MentorSummaryExcerptSpan(
        message_id=message_id, start=start, end=end, kind=kind
    )


class TestSummarizeMentorSessionContextUseCase(MentorResponseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare(MentorResponseStatus.PROCESSING)
        self.identifiers.generate.side_effect = ['summary-new', 'correlation-new']
        self.summarizer = create_autospec(
            MentorConversationSummarizerProvider, instance=True
        )
        self.progress = create_autospec(
            RecordMentorResponseProgressUseCase, instance=True
        )
        self.renew = create_autospec(RenewMentorResponseClaimUseCase, instance=True)
        self.renew.execute.return_value = True
        self.telemetry = create_autospec(MentorTelemetryProvider, instance=True)
        self.messages = tuple(_message(index) for index in range(1, 21))
        self.boundary = MentorSummaryBoundary(
            message_id='m20', created_at=self.messages[-1].created_at
        )
        self.volume = MentorMessageVolume(
            count=20, characters=900, last_message=self.boundary
        )
        self.order: list[str] = []
        self.stored: MentorSessionSummary | None = None
        self.summaries = self.repositories.mentor_session_summaries
        self.summaries.next_version.return_value = 1
        self.summaries.add.side_effect = self._add
        self.summaries.remove.side_effect = self._remove
        self.summaries.find_processing_for_update.side_effect = self._stored
        self.repositories.mentor_sessions.lock_session.side_effect = self._lock
        self.repositories.mentor_messages.measure_unsummarized.side_effect = (
            self._measure
        )
        self.repositories.mentor_messages.find_range.return_value = self.messages
        self.repositories.mentor_messages.find_first_message_id.return_value = 'm01'
        self.repositories.mentor_messages.find_by_ids.return_value = ()
        self.draft = MentorConversationSummaryDraft(
            topics=('range', 'listas'),
            excerpts=(
                _span('m01', 0, 10, MentorSummaryExcerptKind.DOUBT),
                _span('m02', 0, 10, MentorSummaryExcerptKind.GUIDANCE),
            ),
            algorithm_version='textrank-v1',
        )
        self.summarizer.summarize.return_value = self.draft
        self.subject = SummarizeMentorSessionContextUseCase(
            self.database,
            self.summarizer,
            self.access,
            self.clock,
            self.identifiers,
            self.progress,
            self.renew,
            self.telemetry,
        )

    # --- helpers --------------------------------------------------------------

    def _lock(self, *_args: object) -> None:
        self.order.append('lock')

    def _measure(self, *_args: object) -> MentorMessageVolume:
        self.order.append('measure')
        return self.volume

    def _stored(self, *_args: object) -> MentorSessionSummary | None:
        return self.stored

    def _fence(self, *_args: object) -> MentorSession:
        self.order.append('session-fence')
        return self.session

    def _commit(self, *_args: object) -> None:
        self.order.append('commit')

    def _close(self, *_args: object) -> None:
        self.order.append('close')

    def _add(self, row: MentorSessionSummary) -> None:
        self.order.append('add')
        self.stored = row

    def _remove(self, summary_id: str) -> None:
        self.order.append('remove')
        if self.stored is not None and self.stored.id == summary_id:
            self.stored = None

    def processing_row(self, **changes: Any) -> MentorSessionSummary:
        values: dict[str, Any] = {
            'id': 'stale',
            'account_id': 'account',
            'session_id': 'session',
            'attempt_id': 'older-attempt',
            'version': 2,
            'boundary': self.boundary,
            'covered_message_count': 15,
            'first_message_id': 'm01',
            'now': self.now,
        }
        values.update(changes)
        return MentorSessionSummary.start(**values)

    def previous_summary(self) -> MentorSessionSummary:
        started = MentorSessionSummary.start(
            id='previous',
            account_id='account',
            session_id='session',
            attempt_id='old-attempt',
            version=3,
            boundary=MentorSummaryBoundary(
                message_id='p21', created_at=datetime(2026, 10, 9, 12, tzinfo=UTC)
            ),
            covered_message_count=21,
            first_message_id='p01',
            now=datetime(2026, 10, 9, 13, tzinfo=UTC),
        )
        return started.complete(
            MentorConversationSummaryDraft(
                topics=('laços',),
                excerpts=(_span('p03', 0, 12, MentorSummaryExcerptKind.DOUBT),),
                algorithm_version='textrank-v1',
            ),
            datetime(2026, 10, 9, 13, 1, tzinfo=UTC),
        )

    def use_previous(self) -> tuple[MentorSessionSummary, MentorMessage]:
        previous = self.previous_summary()
        source = replace(
            _message(3, 'Meu laço não termina.'),
            id='p03',
            created_at=datetime(2026, 10, 9, tzinfo=UTC),
        )
        self.summaries.find_ready.return_value = previous
        self.repositories.mentor_messages.find_by_ids.return_value = (source,)
        return previous, source

    def interrupt_summarization(self, mutate: Callable[[], None]) -> None:
        def summarize(*_args: object) -> MentorConversationSummaryDraft:
            mutate()
            return self.draft

        self.summarizer.summarize.side_effect = summarize

    def closing_events(self) -> list[Any]:
        return [
            call.args[0]
            for call in self.repositories.mentor_response_events.append.call_args_list
            if call.args[0].progress is None
        ]

    def emitted(self) -> dict[str, Any]:
        self.telemetry.emit.assert_called_once()
        call = self.telemetry.emit.call_args
        return {'stage': call.args[0], **call.kwargs}

    def assert_no_summary_written(self) -> None:
        self.summaries.update.assert_not_called()
        self.summaries.remove_superseded.assert_not_called()
        self.summaries.remove_superseded_failures.assert_not_called()

    # --- trigger ---------------------------------------------------------------

    @pytest.mark.parametrize('with_previous', [False, True])
    @pytest.mark.parametrize(('count', 'characters', 'summarizes'), _THRESHOLD_CASES)
    def test_should_summarize_exactly_at_the_message_or_code_point_threshold(
        self, count: int, characters: int, summarizes: bool, with_previous: bool
    ) -> None:
        if with_previous:
            self.use_previous()
        self.volume = MentorMessageVolume(
            count=count,
            characters=characters,
            last_message=self.boundary if count else None,
        )

        self.subject.execute('attempt', 'owner')

        assert self.summarizer.summarize.called is summarizes
        assert self.summaries.add.called is summarizes
        assert self.progress.execute.called is summarizes
        assert self.telemetry.emit.called is summarizes
        assert bool(self.closing_events()) is summarizes

    def test_should_measure_after_the_previous_boundary_keeping_ten_recent_messages(
        self,
    ) -> None:
        previous, _ = self.use_previous()

        self.subject.execute('attempt', 'owner')

        self.repositories.mentor_messages.measure_unsummarized.assert_called_once_with(
            'account', 'session', previous.boundary, 10
        )

    def test_should_measure_the_whole_conversation_without_a_previous_summary(
        self,
    ) -> None:
        self.subject.execute('attempt', 'owner')

        self.repositories.mentor_messages.measure_unsummarized.assert_called_once_with(
            'account', 'session', None, 10
        )

    def test_should_keep_the_documented_policy_constants(self) -> None:
        assert SummarizeMentorSessionContextUseCase.RECENT_WINDOW == 10
        assert SummarizeMentorSessionContextUseCase.SUMMARY_MESSAGE_THRESHOLD == 20
        assert (
            SummarizeMentorSessionContextUseCase.SUMMARY_CHARACTER_THRESHOLD == 16_000
        )

    def test_should_leave_no_trace_below_the_threshold(self) -> None:
        self.volume = MentorMessageVolume(
            count=19, characters=15_999, last_message=self.boundary
        )

        self.subject.execute('attempt', 'owner')

        self.summaries.add.assert_not_called()
        self.assert_no_summary_written()
        self.progress.execute.assert_not_called()
        self.renew.execute.assert_not_called()
        self.summarizer.summarize.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()
        self.telemetry.emit.assert_not_called()

    # --- start ----------------------------------------------------------------

    def test_should_insert_the_processing_row_only_after_locking_and_fencing_the_session(
        self,
    ) -> None:
        self.repositories.mentor_sessions.find_by_id_for_update.side_effect = (
            self._fence
        )

        self.subject.execute('attempt', 'owner')

        # The claim phase fences the session first; the locked phase follows it.
        locked = self.order[self.order.index('lock') :]
        assert locked[:4] == ['lock', 'session-fence', 'measure', 'add']
        row = self.summaries.add.call_args.args[0]
        assert row.id == 'summary-new'
        assert row.account_id == 'account'
        assert row.session_id == 'session'
        assert row.attempt_id == 'attempt'
        assert row.version == 1
        assert row.status is MentorSummaryStatus.PROCESSING
        assert row.boundary == self.boundary
        assert row.covered_message_count == 20
        assert row.first_message_id == 'm01'
        assert row.topics == ()
        assert row.excerpts == ()
        self.summaries.next_version.assert_called_once_with('session')

    def test_should_record_summarize_context_progress(self) -> None:
        self.subject.execute('attempt', 'owner')

        self.progress.execute.assert_called_once_with(
            'attempt', 'owner', MentorWorkflowStep.SUMMARIZE_CONTEXT
        )

    def test_should_freeze_the_boundary_and_continue_the_covered_count_from_the_previous_summary(
        self,
    ) -> None:
        previous, source = self.use_previous()
        self.summaries.next_version.return_value = 4

        self.subject.execute('attempt', 'owner')

        row = self.summaries.add.call_args.args[0]
        assert row.version == 4
        assert row.boundary == self.boundary
        assert row.covered_message_count == 21 + 20
        assert row.first_message_id == 'p01'
        self.repositories.mentor_messages.find_first_message_id.assert_not_called()
        self.repositories.mentor_messages.find_range.assert_called_once_with(
            'account', 'session', previous.boundary, self.boundary
        )
        self.repositories.mentor_messages.find_by_ids.assert_called_once_with(
            'account', 'session', ('p03',)
        )
        messages, context = self.summarizer.summarize.call_args.args
        assert messages == (source, *self.messages)
        assert len({m.id for m in messages}) == len(messages)
        assert context == MentorConversationSummaryContext.from_summary(
            previous, (source,)
        )

    def test_should_summarize_the_whole_range_when_there_is_no_previous_summary(
        self,
    ) -> None:
        self.subject.execute('attempt', 'owner')

        messages, context = self.summarizer.summarize.call_args.args
        assert messages == self.messages
        assert context is None
        self.repositories.mentor_messages.find_by_ids.assert_not_called()
        self.repositories.mentor_messages.find_range.assert_called_once_with(
            'account', 'session', None, self.boundary
        )
        self.repositories.mentor_messages.find_first_message_id.assert_called_once_with(
            'account', 'session'
        )
        row = self.summaries.add.call_args.args[0]
        assert row.first_message_id == 'm01'
        assert row.covered_message_count == 20

    def test_should_not_load_the_older_history_to_find_the_first_message(
        self,
    ) -> None:
        self.subject.execute('attempt', 'owner')

        # The advisory-locked phase only asks for one id; the range is read once,
        # outside the lock, to build the summary.
        self.repositories.mentor_messages.find_range.assert_called_once()
        self.repositories.mentor_messages.find_all.assert_not_called()

    def test_should_not_insert_a_row_when_the_conversation_has_no_first_message(
        self,
    ) -> None:
        self.repositories.mentor_messages.find_first_message_id.return_value = None

        self.subject.execute('attempt', 'owner')

        self.summaries.add.assert_not_called()
        self.summarizer.summarize.assert_not_called()
        self.progress.execute.assert_not_called()

    def test_should_delete_a_stale_processing_row_of_another_attempt_before_measuring(
        self,
    ) -> None:
        self.stored = self.processing_row()

        self.subject.execute('attempt', 'owner')

        self.summaries.remove.assert_called_once_with('stale')
        assert self.order.index('remove') < self.order.index('measure')
        assert self.summaries.add.call_args.args[0].id == 'summary-new'

    def test_should_remove_a_stale_row_even_when_the_conversation_is_below_the_threshold(
        self,
    ) -> None:
        self.stored = self.processing_row()
        self.volume = MentorMessageVolume(
            count=2, characters=10, last_message=self.boundary
        )

        self.subject.execute('attempt', 'owner')

        self.summaries.remove.assert_called_once_with('stale')
        self.summaries.add.assert_not_called()
        self.summarizer.summarize.assert_not_called()

    def test_should_resume_a_processing_row_of_the_same_attempt_with_its_frozen_boundary(
        self,
    ) -> None:
        frozen = MentorSummaryBoundary(
            message_id='m15', created_at=self.messages[14].created_at
        )
        self.stored = self.processing_row(
            id='resumed', attempt_id='attempt', boundary=frozen, version=1
        )

        self.subject.execute('attempt', 'owner')

        self.summaries.add.assert_not_called()
        self.summaries.remove.assert_not_called()
        self.repositories.mentor_messages.measure_unsummarized.assert_not_called()
        self.repositories.mentor_messages.find_range.assert_called_once_with(
            'account', 'session', None, frozen
        )
        completed = self.summaries.update.call_args.args[0]
        assert completed.id == 'resumed'
        assert completed.boundary == frozen
        assert completed.status is MentorSummaryStatus.READY

    @pytest.mark.parametrize(
        'break_fence',
        [
            'tombstoned',
            'attempt_missing',
            'attempt_cancelled',
            'attempt_superseded',
            'claim_lost',
        ],
    )
    def test_should_not_insert_a_row_when_the_session_or_attempt_fences_fail(
        self, break_fence: str
    ) -> None:
        sessions = self.repositories.mentor_sessions
        attempts = self.repositories.mentor_response_attempts
        # The claim phase succeeds; the fences fail only for the locked insert.
        if break_fence == 'tombstoned':
            sessions.find_by_id_for_update.side_effect = [self.session, None]
        elif break_fence == 'attempt_missing':
            attempts.find_by_id.side_effect = [None]
        elif break_fence == 'attempt_cancelled':
            attempts.find_by_id.side_effect = [
                replace(self.attempt, status=MentorResponseStatus.CANCELLED)
            ]
        elif break_fence == 'attempt_superseded':
            attempts.find_current.side_effect = [
                self.attempt,
                replace(self.attempt, id='newer'),
            ]
        else:
            attempts.has_claim.side_effect = [True, False]

        self.subject.execute('attempt', 'owner')

        self.summaries.add.assert_not_called()
        self.progress.execute.assert_not_called()
        self.summarizer.summarize.assert_not_called()

    def test_should_claim_a_queued_attempt_and_publish_the_processing_status_first(
        self,
    ) -> None:
        attempts = self.repositories.mentor_response_attempts
        attempts.find_by_id_for_update.return_value = replace(
            self.attempt, status=MentorResponseStatus.QUEUED
        )

        self.subject.execute('attempt', 'owner')

        attempts.claim.assert_called_once_with(
            'attempt', 'owner', self.now, self.now + timedelta(minutes=5), 'revision'
        )
        attempts.transition.assert_called_once_with(
            'attempt',
            MentorResponseStatus.QUEUED,
            MentorResponseStatus.PROCESSING,
            'revision',
        )
        first = self.repositories.mentor_response_events.append.call_args_list[0]
        assert first.args[0].kind is MentorResponseEventKind.STATUS
        assert first.args[0].status is MentorResponseStatus.PROCESSING
        assert first.args[0].progress is None

    # --- success --------------------------------------------------------------

    def test_should_complete_the_row_and_remove_superseded_versions(self) -> None:
        self.subject.execute('attempt', 'owner')

        completed = self.summaries.update.call_args.args[0]
        assert completed.id == 'summary-new'
        assert completed.status is MentorSummaryStatus.READY
        assert completed.topics == ('range', 'listas')
        assert completed.excerpts == self.draft.excerpts
        assert completed.algorithm_version == 'textrank-v1'
        assert completed.completed_at == self.now
        assert completed.failure_code is None
        self.summaries.remove_superseded.assert_called_once_with(
            'session', 'summary-new'
        )
        # remove_superseded already drops ready and failed rows (CA-04 coexisting
        # ready + failed is replaced by the next ready one).
        self.summaries.remove_superseded_failures.assert_not_called()

    def test_should_remove_the_superseded_ready_row_before_marking_the_new_one_ready(
        self,
    ) -> None:
        self.subject.execute('attempt', 'owner')

        calls = [call[0] for call in self.summaries.method_calls]
        assert calls.index('remove_superseded') < calls.index('update')

    def test_should_renew_the_attempt_lease_before_summarizing_outside_a_transaction(
        self,
    ) -> None:
        def renew(*_args: object) -> bool:
            self.order.append('renew')
            return True

        def summarize(*_args: object) -> MentorConversationSummaryDraft:
            self.order.append('summarize')
            return self.draft

        self.renew.execute.side_effect = renew
        self.summarizer.summarize.side_effect = summarize
        self.database.transaction.return_value.__exit__.side_effect = self._commit

        self.subject.execute('attempt', 'owner')

        assert self.order.index('renew') < self.order.index('summarize')
        # No transaction is open around the summarizer call.
        before = self.order[: self.order.index('renew')]
        assert before[-1] == 'commit'
        assert self.order.index('renew') + 1 == self.order.index('summarize')
        self.renew.execute.assert_called_once_with('attempt', 'owner')

    def test_should_record_no_usage_or_quota_effect(self) -> None:
        self.subject.execute('attempt', 'owner')

        self.access.record_usage.assert_not_called()
        self.repositories.mentor_response_attempts.journal_usage.assert_not_called()
        self.repositories.mentor_response_attempts.reserve_generation.assert_not_called()

    # --- failures -------------------------------------------------------------

    @pytest.mark.parametrize(
        ('error', 'code'),
        [
            (OSError('model missing'), MentorSummaryFailureCode.NLP_UNAVAILABLE),
            (ServiceUnavailableError(), MentorSummaryFailureCode.NLP_UNAVAILABLE),
            (
                OperationalError('select 1', {}, Exception('lost')),
                MentorSummaryFailureCode.EXHAUSTED,
            ),
            (RuntimeError('unexpected'), MentorSummaryFailureCode.EXHAUSTED),
        ],
    )
    def test_should_mark_the_row_failed_with_a_closed_code_when_the_summarizer_fails(
        self, error: Exception, code: MentorSummaryFailureCode
    ) -> None:
        self.summarizer.summarize.side_effect = error

        self.subject.execute('attempt', 'owner')

        failed = self.summaries.update.call_args.args[0]
        assert failed.id == 'summary-new'
        assert failed.status is MentorSummaryStatus.FAILED
        assert failed.failure_code is code
        assert failed.topics == ()
        assert failed.excerpts == ()
        assert failed.completed_at is None
        self.summaries.remove_superseded.assert_not_called()
        self.summaries.remove_superseded_failures.assert_called_once_with(
            'session', 'summary-new'
        )
        assert len(self.closing_events()) == 1
        assert self.emitted()['outcome'] == 'failed'
        assert self.emitted()['failure_code'] is code

    def test_should_fail_with_exhausted_when_loading_the_range_fails(self) -> None:
        self.repositories.mentor_messages.find_range.side_effect = OperationalError(
            'select 1', {}, Exception('lost')
        )

        self.subject.execute('attempt', 'owner')

        failed = self.summaries.update.call_args.args[0]
        assert failed.failure_code is MentorSummaryFailureCode.EXHAUSTED
        self.summarizer.summarize.assert_not_called()

    def test_should_keep_the_previous_ready_summary_when_the_new_one_fails(
        self,
    ) -> None:
        self.use_previous()
        self.summarizer.summarize.side_effect = OSError('model missing')

        self.subject.execute('attempt', 'owner')

        self.summaries.remove_superseded.assert_not_called()
        self.summaries.remove.assert_not_called()
        assert self.summaries.update.call_args.args[0].status is (
            MentorSummaryStatus.FAILED
        )

    def test_should_keep_exactly_one_failed_row_by_pruning_older_failures_first(
        self,
    ) -> None:
        self.use_previous()
        self.summarizer.summarize.side_effect = OSError('model missing')

        self.subject.execute('attempt', 'owner')

        self.summaries.remove_superseded_failures.assert_called_once_with(
            'session', 'summary-new'
        )
        calls = [call[0] for call in self.summaries.method_calls]
        assert calls.index('remove_superseded_failures') < calls.index('update')

    def test_should_replace_a_coexisting_ready_and_failed_pair_when_the_next_one_is_ready(
        self,
    ) -> None:
        self.use_previous()

        self.subject.execute('attempt', 'owner')

        self.summaries.remove_superseded.assert_called_once_with(
            'session', 'summary-new'
        )
        self.summaries.remove_superseded_failures.assert_not_called()
        assert self.summaries.update.call_args.args[0].status is (
            MentorSummaryStatus.READY
        )

    @pytest.mark.parametrize(
        'invalid_draft',
        [
            pytest.param(
                [_span('other', 0, 5, MentorSummaryExcerptKind.DOUBT)], id='foreign'
            ),
            pytest.param(
                [_span('m01', 0, 0, MentorSummaryExcerptKind.DOUBT)], id='empty'
            ),
            pytest.param(
                [_span('m01', 5, 3, MentorSummaryExcerptKind.DOUBT)], id='reversed'
            ),
            pytest.param(
                [_span('m01', -1, 4, MentorSummaryExcerptKind.DOUBT)], id='negative'
            ),
            pytest.param(
                [_span('m01', 0, 9_999, MentorSummaryExcerptKind.DOUBT)],
                id='past-the-message',
            ),
            pytest.param(
                [_span('m01', 0, 281, MentorSummaryExcerptKind.DOUBT)],
                id='over-280-code-points',
            ),
            pytest.param(
                [_span('m01', 3, 4, MentorSummaryExcerptKind.DOUBT)], id='blank'
            ),
            pytest.param(
                [_span('m01', 0, 4, MentorSummaryExcerptKind.DOUBT)] * 6,
                id='six-doubts',
            ),
            pytest.param(
                [_span('m02', 0, 4, MentorSummaryExcerptKind.GUIDANCE)] * 6,
                id='six-guidance',
            ),
        ],
    )
    def test_should_mark_the_row_invalid_output_for_out_of_contract_spans(
        self, invalid_draft: list[MentorSummaryExcerptSpan]
    ) -> None:
        self.messages = replace_message(
            self.messages, 0, 'Meu laço não mostra o último.'
        )
        self.repositories.mentor_messages.find_range.return_value = self.messages
        self.summarizer.summarize.return_value = replace(
            self.draft, excerpts=tuple(invalid_draft)
        )

        self.subject.execute('attempt', 'owner')

        failed = self.summaries.update.call_args.args[0]
        assert failed.status is MentorSummaryStatus.FAILED
        assert failed.failure_code is MentorSummaryFailureCode.INVALID_OUTPUT
        self.summaries.remove_superseded.assert_not_called()
        assert self.emitted()['failure_code'] is MentorSummaryFailureCode.INVALID_OUTPUT

    def test_should_accept_a_span_of_exactly_280_code_points(self) -> None:
        content = 'á' * 400
        self.messages = replace_message(self.messages, 0, content)
        self.repositories.mentor_messages.find_range.return_value = self.messages
        self.summarizer.summarize.return_value = replace(
            self.draft,
            excerpts=(_span('m01', 0, 280, MentorSummaryExcerptKind.DOUBT),),
        )

        self.subject.execute('attempt', 'owner')

        assert self.summaries.update.call_args.args[0].status is (
            MentorSummaryStatus.READY
        )

    @pytest.mark.parametrize(
        'topics',
        [
            pytest.param(tuple(f'assunto {n}' for n in range(9)), id='nine-topics'),
            pytest.param(('',), id='empty-topic'),
            pytest.param(('x' * 81,), id='long-topic'),
        ],
    )
    def test_should_mark_the_row_invalid_output_for_out_of_contract_topics(
        self, topics: tuple[str, ...]
    ) -> None:
        self.summarizer.summarize.return_value = replace(self.draft, topics=topics)

        self.subject.execute('attempt', 'owner')

        assert self.summaries.update.call_args.args[0].failure_code is (
            MentorSummaryFailureCode.INVALID_OUTPUT
        )

    def test_should_mark_the_row_invalid_output_for_an_empty_draft(self) -> None:
        self.summarizer.summarize.return_value = replace(
            self.draft, topics=(), excerpts=()
        )

        self.subject.execute('attempt', 'owner')

        assert self.summaries.update.call_args.args[0].failure_code is (
            MentorSummaryFailureCode.INVALID_OUTPUT
        )

    @pytest.mark.parametrize(
        ('content', 'start', 'end', 'valid'),
        [
            pytest.param(
                'Antes.\n```python\nfor i in range(3):\n    print(i)\n```\nDepois.',
                0,
                6,
                True,
                id='before-the-fence',
            ),
            pytest.param(
                'Antes.\n```python\nfor i in range(3):\n    print(i)\n```\nDepois.',
                53,
                60,
                True,
                id='after-the-fence',
            ),
            pytest.param(
                'Antes.\n```python\nfor i in range(3):\n    print(i)\n```\nDepois.',
                18,
                35,
                False,
                id='inside-the-fence',
            ),
            pytest.param(
                'Antes.\n```python\nfor i in range(3):\n    print(i)\n```\nDepois.',
                3,
                25,
                False,
                id='overlapping-the-fence-start',
            ),
            pytest.param(
                'Veja.\n~~~\nprint(1)\n~~~\nFim.', 6, 18, False, id='tilde-fence'
            ),
            pytest.param(
                'Veja.\n```\nprint(1)\nsem fechar', 6, 28, False, id='unclosed-fence'
            ),
            pytest.param(
                'Use `range(3)` no laço.', 0, 23, True, id='inline-code-is-allowed'
            ),
        ],
    )
    def test_should_reject_excerpts_that_touch_fenced_code(
        self, content: str, start: int, end: int, valid: bool
    ) -> None:
        self.messages = replace_message(self.messages, 0, content)
        self.repositories.mentor_messages.find_range.return_value = self.messages
        self.summarizer.summarize.return_value = replace(
            self.draft,
            excerpts=(_span('m01', start, end, MentorSummaryExcerptKind.DOUBT),),
        )

        self.subject.execute('attempt', 'owner')

        written = self.summaries.update.call_args.args[0]
        assert (written.status is MentorSummaryStatus.READY) is valid
        if not valid:
            assert written.failure_code is MentorSummaryFailureCode.INVALID_OUTPUT

    def test_should_accept_previous_excerpts_folded_into_the_new_summary(self) -> None:
        _, source = self.use_previous()
        self.summarizer.summarize.return_value = replace(
            self.draft,
            excerpts=(
                _span(source.id, 0, 12, MentorSummaryExcerptKind.DOUBT),
                _span('m02', 0, 10, MentorSummaryExcerptKind.GUIDANCE),
            ),
        )

        self.subject.execute('attempt', 'owner')

        assert self.summaries.update.call_args.args[0].status is (
            MentorSummaryStatus.READY
        )
        self.summaries.remove_superseded.assert_called_once_with(
            'session', 'summary-new'
        )

    # --- fences at commit -----------------------------------------------------

    @pytest.mark.parametrize(
        ('name', 'still_current'),
        [
            ('tombstoned', False),
            ('attempt_cancelled', False),
            ('attempt_superseded', False),
            ('claim_lost', False),
            ('row_gone', True),
            ('row_replaced', True),
            ('access_revision_changed', True),
            ('inactive_account', True),
        ],
    )
    def test_should_discard_the_result_without_writes_when_a_fence_fails_at_commit(
        self, name: str, still_current: bool
    ) -> None:
        sessions = self.repositories.mentor_sessions
        attempts = self.repositories.mentor_response_attempts

        def break_fence() -> None:
            if name == 'tombstoned':
                sessions.find_by_id_for_update.return_value = None
            elif name == 'attempt_cancelled':
                attempts.find_by_id.return_value = replace(
                    self.attempt, status=MentorResponseStatus.CANCELLED
                )
            elif name == 'attempt_superseded':
                attempts.find_current.return_value = replace(self.attempt, id='newer')
            elif name == 'claim_lost':
                attempts.has_claim.return_value = False
            elif name == 'row_gone':
                self.stored = None
            elif name == 'row_replaced':
                self.stored = self.processing_row(id='another-row')
            elif name == 'access_revision_changed':
                self.access.assert_current.side_effect = AuthorizationError()
            else:
                self.access.assert_current.side_effect = AuthorizationError()

        self.interrupt_summarization(break_fence)

        self.subject.execute('attempt', 'owner')

        self.assert_no_summary_written()
        assert self.emitted()['outcome'] == 'discarded'
        assert self.emitted()['failure_code'] is None
        # The closing event only exists while the attempt is still current.
        assert bool(self.closing_events()) is still_current

    def test_should_not_write_a_failure_when_a_fence_fails_after_the_summarizer_raised(
        self,
    ) -> None:
        def cancel() -> None:
            self.repositories.mentor_response_attempts.find_by_id.return_value = (
                replace(self.attempt, status=MentorResponseStatus.CANCELLED)
            )
            raise OSError('model missing')

        self.interrupt_summarization(cancel)

        self.subject.execute('attempt', 'owner')

        self.assert_no_summary_written()
        assert self.emitted()['outcome'] == 'discarded'
        assert not self.closing_events()

    def test_should_keep_a_summary_committed_before_the_cancel(self) -> None:
        self.subject.execute('attempt', 'owner')

        committed = self.summaries.update.call_args.args[0]
        assert committed.status is MentorSummaryStatus.READY
        self.summaries.remove.assert_not_called()

    # --- access ---------------------------------------------------------------

    def test_should_not_start_when_the_account_is_inactive_before_reading_messages(
        self,
    ) -> None:
        self.access.assert_current.side_effect = AuthorizationError()

        self.subject.execute('attempt', 'owner')

        self.repositories.mentor_messages.measure_unsummarized.assert_not_called()
        self.repositories.mentor_messages.find_range.assert_not_called()
        self.summaries.add.assert_not_called()
        self.progress.execute.assert_not_called()
        self.summarizer.summarize.assert_not_called()

    def test_should_delete_the_row_without_a_notice_when_access_is_lost_after_starting(
        self,
    ) -> None:
        def lose_access(*_args: object) -> None:
            self.access.assert_current.side_effect = AuthorizationError()

        self.progress.execute.side_effect = lose_access

        self.subject.execute('attempt', 'owner')

        self.summaries.remove.assert_called_once_with('summary-new')
        self.summarizer.summarize.assert_not_called()
        self.repositories.mentor_messages.find_by_ids.assert_not_called()
        self.assert_no_summary_written()
        assert self.emitted()['outcome'] == 'discarded'
        assert len(self.closing_events()) == 1

    def test_should_discard_when_the_progress_event_cannot_be_recorded(self) -> None:
        self.progress.execute.side_effect = ServiceUnavailableError()

        self.subject.execute('attempt', 'owner')

        self.summarizer.summarize.assert_not_called()
        self.assert_no_summary_written()
        assert self.emitted()['outcome'] == 'discarded'

    @pytest.mark.parametrize('renewal', [False, AuthorizationError()])
    def test_should_discard_when_the_lease_cannot_be_renewed(
        self, renewal: bool | Exception
    ) -> None:
        if isinstance(renewal, Exception):
            self.renew.execute.side_effect = renewal
        else:
            self.renew.execute.return_value = renewal

        self.subject.execute('attempt', 'owner')

        self.summarizer.summarize.assert_not_called()
        self.assert_no_summary_written()
        assert self.emitted()['outcome'] == 'discarded'

    # --- closing event --------------------------------------------------------

    def test_should_close_progress_with_a_null_progress_status_event(self) -> None:
        self.subject.execute('attempt', 'owner')

        (event,) = self.closing_events()
        assert event.kind is MentorResponseEventKind.STATUS
        assert event.status is MentorResponseStatus.PROCESSING
        assert event.progress is None
        assert event.block is None
        assert event.session_id == 'session'
        assert event.attempt_id == 'attempt'
        assert event.sequence == 2
        self.repositories.mentor_response_events.next_sequence.assert_called_with(
            'session'
        )

    @pytest.mark.parametrize('outcome', ['ready', 'failed', 'discarded'])
    def test_should_close_progress_in_every_outcome_while_the_attempt_is_current(
        self, outcome: str
    ) -> None:
        if outcome == 'failed':
            self.summarizer.summarize.side_effect = OSError('model missing')
        if outcome == 'discarded':
            self.renew.execute.return_value = False

        self.subject.execute('attempt', 'owner')

        assert len(self.closing_events()) == 1
        assert self.emitted()['outcome'] == outcome

    def test_should_close_progress_under_the_session_lock(self) -> None:
        self.repositories.mentor_response_events.append.side_effect = self._close

        self.subject.execute('attempt', 'owner')

        assert self.order[-2:] == ['lock', 'close']

    # --- never raises ---------------------------------------------------------

    @pytest.mark.parametrize(
        'break_point',
        [
            'transaction',
            'claim',
            'deadlock',
            'attempt_lookup',
            'access',
            'lock_session',
            'measure',
            'duplicate_active_row',
            'version',
            'identifier',
        ],
    )
    def test_should_never_raise_and_never_summarize_when_the_start_phase_breaks(
        self, break_point: str
    ) -> None:
        operational = OperationalError('select 1', {}, Exception('deadlock detected'))
        attempts = self.repositories.mentor_response_attempts
        if break_point == 'transaction':
            self.database.transaction.side_effect = operational
        elif break_point == 'claim':
            attempts.claim.return_value = False
        elif break_point == 'deadlock':
            attempts.claim.side_effect = operational
        elif break_point == 'attempt_lookup':
            attempts.find_by_id_for_update.return_value = None
        elif break_point == 'access':
            self.access.assert_current.side_effect = ServiceUnavailableError()
        elif break_point == 'lock_session':
            self.repositories.mentor_sessions.lock_session.side_effect = operational
        elif break_point == 'measure':
            self.repositories.mentor_messages.measure_unsummarized.side_effect = (
                operational
            )
        elif break_point == 'duplicate_active_row':
            self.summaries.add.side_effect = ConflictError()
        elif break_point == 'version':
            self.summaries.next_version.side_effect = operational
        else:
            self.identifiers.generate.side_effect = RuntimeError('ids unavailable')

        self.subject.execute('attempt', 'owner')

        self.summarizer.summarize.assert_not_called()
        self.progress.execute.assert_not_called()
        self.assert_no_summary_written()

    def test_should_never_raise_when_the_final_write_breaks(self) -> None:
        self.summaries.update.side_effect = OperationalError(
            'update', {}, Exception('lost')
        )

        self.subject.execute('attempt', 'owner')

        assert self.emitted()['outcome'] == 'discarded'
        self.summaries.remove_superseded.assert_called_once()
        assert len(self.closing_events()) == 1

    def test_should_never_raise_when_pruning_older_failures_breaks(self) -> None:
        self.summarizer.summarize.side_effect = OSError('model missing')
        self.summaries.remove_superseded_failures.side_effect = OperationalError(
            'delete', {}, Exception('lost')
        )

        self.subject.execute('attempt', 'owner')

        self.summaries.update.assert_not_called()
        assert self.emitted()['outcome'] == 'discarded'

    def test_should_never_raise_when_closing_the_progress_breaks(self) -> None:
        self.repositories.mentor_response_events.append.side_effect = OperationalError(
            'insert', {}, Exception('lost')
        )

        self.subject.execute('attempt', 'owner')

        assert self.emitted()['outcome'] == 'ready'
        assert self.summaries.update.call_args.args[0].status is (
            MentorSummaryStatus.READY
        )
        self.summaries.remove_superseded.assert_called_once_with(
            'session', 'summary-new'
        )

    def test_should_not_close_progress_when_the_claim_is_lost_after_the_summary(
        self,
    ) -> None:
        attempts = self.repositories.mentor_response_attempts

        def has_claim(*_args: object) -> bool:
            return not self.summaries.update.called

        attempts.has_claim.side_effect = has_claim

        self.subject.execute('attempt', 'owner')

        assert self.closing_events() == []
        assert self.summaries.update.call_args.args[0].status is (
            MentorSummaryStatus.READY
        )
        assert self.emitted()['outcome'] == 'ready'

    # --- telemetry ------------------------------------------------------------

    def test_should_emit_one_allowlisted_span_without_identifiers_or_text(self) -> None:
        self.subject.execute('attempt', 'owner')

        emitted = self.emitted()
        assert emitted == {
            'stage': 'summarize',
            'correlation_id': 'correlation-new',
            'profile': 'local',
            'duration_ms': 0.0,
            'counts': {'messages': 20, 'topics': 2, 'excerpts': 2},
            'outcome': 'ready',
            'failure_code': None,
        }
        private = {'account', 'session', 'attempt', 'owner', 'summary-new', 'm01'}
        assert private.isdisjoint(str(value) for value in emitted.values())
        assert all(isinstance(count, int) for count in emitted['counts'].values())

    def test_should_count_only_the_newly_summarized_messages_with_a_previous_summary(
        self,
    ) -> None:
        self.use_previous()
        self.volume = MentorMessageVolume(
            count=25, characters=900, last_message=self.boundary
        )

        self.subject.execute('attempt', 'owner')

        assert self.emitted()['counts']['messages'] == 25

    def test_should_measure_the_duration_with_the_injected_clock(self) -> None:
        later = self.now + timedelta(milliseconds=1_500)
        self.clock.now.side_effect = None
        ticks = iter([self.now] * 40)
        stamps: list[datetime] = []

        def now() -> datetime:
            stamps.append(self.now)
            return later if self.summarizer.summarize.called else next(ticks)

        self.clock.now.side_effect = now

        self.subject.execute('attempt', 'owner')

        assert self.emitted()['duration_ms'] == pytest.approx(1_500)

    def test_should_not_change_the_result_when_telemetry_fails(self) -> None:
        self.telemetry.emit.side_effect = RuntimeError('telemetry down')

        self.subject.execute('attempt', 'owner')

        assert self.summaries.update.call_args.args[0].status is (
            MentorSummaryStatus.READY
        )
        assert len(self.closing_events()) == 1


def replace_message(
    messages: tuple[MentorMessage, ...], index: int, content: str
) -> tuple[MentorMessage, ...]:
    return tuple(
        replace(message, content=content) if position == index else message
        for position, message in enumerate(messages)
    )

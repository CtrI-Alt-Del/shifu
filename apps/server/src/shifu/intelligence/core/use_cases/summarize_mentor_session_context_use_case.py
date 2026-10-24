from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal

from shifu.intelligence.core.domain.entities import (
    MentorMessage,
    MentorResponseAttempt,
    MentorSessionSummary,
)
from shifu.intelligence.core.domain.enums import (
    MentorResponseEventKind,
    MentorResponseStatus,
    MentorSummaryFailureCode,
    MentorSummaryStatus,
    MentorWorkflowStep,
)
from shifu.intelligence.core.domain.structures import (
    MentorConversationSummaryContext,
    MentorConversationSummaryDraft,
    MentorMessageVolume,
    fenced_code_ranges,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    MentorConversationSummarizerProvider,
    MentorTelemetryProvider,
)
from shifu.intelligence.core.use_cases.mentor_response_phase_helpers import (
    assert_response_access,
    assert_response_current,
    response_event,
    start_response_attempt,
)
from shifu.intelligence.core.use_cases.record_mentor_response_progress_use_case import (
    RecordMentorResponseProgressUseCase,
)
from shifu.intelligence.core.use_cases.renew_mentor_response_claim_use_case import (
    RenewMentorResponseClaimUseCase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
)

type _Outcome = Literal['ready', 'failed', 'discarded']


@dataclass(frozen=True, slots=True)
class _Plan:
    row: MentorSessionSummary
    previous: MentorSessionSummary | None


@dataclass(frozen=True, slots=True)
class _Discard:
    """The result must not be written; the processing row is removed when fenced."""


@dataclass(frozen=True, slots=True)
class _Failure:
    code: MentorSummaryFailureCode


@dataclass(frozen=True, slots=True)
class _Draft:
    draft: MentorConversationSummaryDraft
    sources: tuple[MentorMessage, ...]


type _Result = _Discard | _Failure | _Draft


class SummarizeMentorSessionContextUseCase:
    """Summarize the older part of a long conversation before the answer is prepared.

    The step is extractive, local and fenced against cancel, deletion and account
    loss. ``execute`` never raises: any error ends the step normally so the answer
    run continues with the previous summary (or none) plus the later messages.
    """

    SUMMARY_MESSAGE_THRESHOLD: ClassVar[int] = 20
    SUMMARY_CHARACTER_THRESHOLD: ClassVar[int] = 16_000
    RECENT_WINDOW: ClassVar[int] = 10
    EXCERPT_MAX_CODE_POINTS: ClassVar[int] = (
        MentorConversationSummaryContext.EXCERPT_MAX_CODE_POINTS
    )
    TELEMETRY_STAGE: ClassVar[str] = 'summarize'
    TELEMETRY_PROFILE: ClassVar[str] = 'local'

    def __init__(
        self,
        database: IntelligenceDatabase,
        summarizer: MentorConversationSummarizerProvider,
        access_provider: MentorAccessProvider,
        clock_provider: ClockProvider,
        identifier_provider: IdentifierProvider,
        progress: RecordMentorResponseProgressUseCase,
        renew_claim: RenewMentorResponseClaimUseCase,
        telemetry: MentorTelemetryProvider,
    ) -> None:
        self._database = database
        self._summarizer = summarizer
        self._access_provider = access_provider
        self._clock_provider = clock_provider
        self._identifier_provider = identifier_provider
        self._progress = progress
        self._renew_claim = renew_claim
        self._telemetry = telemetry

    def execute(self, attempt_id: str, execution_owner: str) -> None:
        try:
            self._run(attempt_id, execution_owner)
        except Exception:  # noqa: BLE001 - the summary step must never fail the answer run.
            return

    def _run(self, attempt_id: str, owner: str) -> None:
        attempt = start_response_attempt(
            self._database,
            self._clock_provider,
            self._access_provider,
            attempt_id,
            owner,
        )
        if attempt is None:
            return
        plan = self._open(attempt, owner)
        if plan is None:
            return

        started_at = self._clock_provider.now()
        result = self._produce(attempt, owner, plan)
        outcome, code = self._settle(attempt, owner, plan, result)
        self._close(attempt, owner)
        self._emit(started_at, plan, result, outcome, code)

    def _open(self, attempt: MentorResponseAttempt, owner: str) -> _Plan | None:
        """Drop stale rows, measure the volume and insert the processing row."""
        account_id, session_id = attempt.account_id, attempt.session_id
        assert_response_access(self._access_provider, attempt)
        with self._database.transaction() as repositories:
            repositories.mentor_sessions.lock_session(account_id, session_id)
            assert_response_current(repositories, attempt, owner, self._clock_provider)
            summaries = repositories.mentor_session_summaries
            ready = summaries.find_ready(account_id, session_id)
            pending = summaries.find_processing_for_update(account_id, session_id)
            if pending is not None and pending.attempt_id == attempt.id:
                return _Plan(row=pending, previous=ready)
            if pending is not None:
                summaries.remove(pending.id)

            volume = repositories.mentor_messages.measure_unsummarized(
                account_id,
                session_id,
                ready.boundary if ready is not None else None,
                self.RECENT_WINDOW,
            )
            if not self._is_long(volume) or volume.last_message is None:
                return None

            first_message_id = (
                ready.first_message_id
                if ready is not None
                else repositories.mentor_messages.find_first_message_id(
                    account_id, session_id
                )
            )
            if first_message_id is None:
                return None
            row = MentorSessionSummary.start(
                id=self._identifier_provider.generate(),
                account_id=account_id,
                session_id=session_id,
                attempt_id=attempt.id,
                version=summaries.next_version(session_id),
                boundary=volume.last_message,
                covered_message_count=(
                    (ready.covered_message_count if ready is not None else 0)
                    + volume.count
                ),
                first_message_id=first_message_id,
                now=self._clock_provider.now(),
            )
            summaries.add(row)
            return _Plan(row=row, previous=ready)

    @classmethod
    def _is_long(cls, volume: MentorMessageVolume) -> bool:
        return (
            volume.count >= cls.SUMMARY_MESSAGE_THRESHOLD
            or volume.characters >= cls.SUMMARY_CHARACTER_THRESHOLD
        )

    def _produce(
        self, attempt: MentorResponseAttempt, owner: str, plan: _Plan
    ) -> _Result:
        try:
            self._progress.execute(
                attempt.id, owner, MentorWorkflowStep.SUMMARIZE_CONTEXT
            )
            assert_response_access(self._access_provider, attempt)
        except Exception:  # noqa: BLE001 - a lost claim or access discards silently.
            return _Discard()

        try:
            messages, previous, previous_messages = self._load(plan)
        except Exception:  # noqa: BLE001 - any load error ends as a closed code.
            return _Failure(MentorSummaryFailureCode.EXHAUSTED)

        try:
            if not self._renew_claim.execute(attempt.id, owner):
                return _Discard()
        except Exception:  # noqa: BLE001 - a lost claim or access discards silently.
            return _Discard()

        # Previous excerpt sources travel with the range so the provider can turn
        # previous excerpts back into spans; order is (created_at, id), no duplicates.
        sources = tuple(
            sorted(
                {m.id: m for m in (*previous_messages, *messages)}.values(),
                key=lambda message: (message.created_at, message.id),
            )
        )
        try:
            draft = self._summarizer.summarize(sources, previous)
        except (OSError, ServiceUnavailableError):
            return _Failure(MentorSummaryFailureCode.NLP_UNAVAILABLE)
        except Exception:  # noqa: BLE001 - provider failures map to a closed code.
            return _Failure(MentorSummaryFailureCode.EXHAUSTED)
        return _Draft(draft=draft, sources=sources)

    def _load(
        self, plan: _Plan
    ) -> tuple[
        tuple[MentorMessage, ...],
        MentorConversationSummaryContext | None,
        tuple[MentorMessage, ...],
    ]:
        row, previous = plan.row, plan.previous
        with self._database.transaction() as repositories:
            messages = repositories.mentor_messages.find_range(
                row.account_id,
                row.session_id,
                previous.boundary if previous is not None else None,
                row.boundary,
            )
            previous_messages = (
                repositories.mentor_messages.find_by_ids(
                    row.account_id,
                    row.session_id,
                    tuple(dict.fromkeys(span.message_id for span in previous.excerpts)),
                )
                if previous is not None
                else ()
            )
        context = (
            MentorConversationSummaryContext.from_summary(previous, previous_messages)
            if previous is not None
            else None
        )
        return messages, context, previous_messages

    def _settle(
        self, attempt: MentorResponseAttempt, owner: str, plan: _Plan, result: _Result
    ) -> tuple[_Outcome, MentorSummaryFailureCode | None]:
        """Write the outcome under the session lock; any fence failure writes nothing."""
        try:
            with self._database.transaction() as repositories:
                repositories.mentor_sessions.lock_session(
                    attempt.account_id, attempt.session_id
                )
                assert_response_current(
                    repositories, attempt, owner, self._clock_provider
                )
                summaries = repositories.mentor_session_summaries
                row = summaries.find_processing_for_update(
                    attempt.account_id, attempt.session_id
                )
                if row is None or row.id != plan.row.id:
                    return 'discarded', None
                if isinstance(result, _Discard):
                    summaries.remove(row.id)
                    return 'discarded', None

                assert_response_access(self._access_provider, attempt)
                finished = self._finish(row, result)
                if finished.status is MentorSummaryStatus.READY:
                    summaries.remove_superseded(row.session_id, finished.id)
                    summaries.update(finished)
                    return 'ready', None
                summaries.remove_superseded_failures(row.session_id, finished.id)
                summaries.update(finished)
                return 'failed', finished.failure_code
        except Exception:  # noqa: BLE001 - fence failures discard without a notice.
            return 'discarded', None

    def _finish(
        self, row: MentorSessionSummary, result: _Failure | _Draft
    ) -> MentorSessionSummary:
        now = self._clock_provider.now()
        if isinstance(result, _Failure):
            return row.fail(result.code, now)
        try:
            self._validate(result.draft, result.sources)
            return row.complete(result.draft, now)
        except ValueError:
            return row.fail(MentorSummaryFailureCode.INVALID_OUTPUT, now)

    @classmethod
    def _validate(
        cls, draft: MentorConversationSummaryDraft, sources: tuple[MentorMessage, ...]
    ) -> None:
        by_id = {message.id: message for message in sources}
        fences: dict[str, tuple[tuple[int, int], ...]] = {}
        for span in draft.excerpts:
            message = by_id.get(span.message_id)
            if message is None:
                raise ValueError('Excerpt outside the covered messages')
            if (
                not 0 <= span.start < span.end <= len(message.content)
                or span.end - span.start > cls.EXCERPT_MAX_CODE_POINTS
                or not message.content[span.start : span.end].strip()
            ):
                raise ValueError('Excerpt outside its source message')
            ranges = fences.setdefault(message.id, fenced_code_ranges(message.content))
            if any(span.start < end and span.end > start for start, end in ranges):
                raise ValueError('Excerpt inside fenced code')

    def _close(self, attempt: MentorResponseAttempt, owner: str) -> None:
        """Clear the ``summarize-context`` progress while the attempt is current."""
        with suppress(Exception), self._database.transaction() as repositories:
            repositories.mentor_sessions.lock_session(
                attempt.account_id, attempt.session_id
            )
            assert_response_current(repositories, attempt, owner, self._clock_provider)
            repositories.mentor_response_events.append(
                response_event(
                    attempt,
                    self._clock_provider,
                    repositories.mentor_response_events.next_sequence(
                        attempt.session_id
                    ),
                    MentorResponseEventKind.STATUS,
                    MentorResponseStatus.PROCESSING,
                )
            )

    def _emit(
        self,
        started_at: datetime,
        plan: _Plan,
        result: _Result,
        outcome: _Outcome,
        code: MentorSummaryFailureCode | None,
    ) -> None:
        with suppress(Exception):
            counts = {
                'messages': plan.row.covered_message_count
                - (plan.previous.covered_message_count if plan.previous else 0)
            }
            if outcome == 'ready' and isinstance(result, _Draft):
                counts['topics'] = len(result.draft.topics)
                counts['excerpts'] = len(result.draft.excerpts)
            self._telemetry.emit(
                self.TELEMETRY_STAGE,
                correlation_id=self._identifier_provider.generate(),
                profile=self.TELEMETRY_PROFILE,
                duration_ms=(
                    (self._clock_provider.now() - started_at).total_seconds() * 1000
                ),
                counts=counts,
                outcome=outcome,
                failure_code=code,
            )

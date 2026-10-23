import logging
from dataclasses import dataclass
from enum import StrEnum

from shifu.intelligence.core.domain.entities import (
    LearnerMemory,
    LearnerMemoryChange,
    MentorMessage,
    MentorResponseAttempt,
)
from shifu.intelligence.core.domain.enums import (
    LearnerMemoryChangeKind,
    MentorMessageRole,
)
from shifu.intelligence.core.domain.structures import (
    LearnerMemoryAnalysis,
    LearnerMemoryOrigin,
    LearnerMemoryStatement,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    LearnerMemoryAnalyzerProvider,
    LearnerMemorySimilarityProvider,
)
from shifu.intelligence.core.use_cases.mentor_response_phase_helpers import (
    assert_response_access,
    assert_response_current,
    start_response_attempt,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
)

_logger = logging.getLogger(__name__)


class _Failure(StrEnum):
    """Closed failure categories; logs carry these and counts, never text."""

    ATTEMPT_UNAVAILABLE = 'attempt_unavailable'
    ANALYSIS_FAILED = 'analysis_failed'
    COMMIT_REJECTED = 'commit_rejected'
    UNEXPECTED = 'unexpected'


@dataclass(frozen=True, slots=True)
class _Pending:
    attempt: MentorResponseAttempt
    message: MentorMessage


@dataclass(slots=True)
class _Outcome:
    created: int = 0
    updated: int = 0
    discarded: int = 0


class UpdateLearnerMemoriesUseCase:
    """Create or update learner memories from the current learner message.

    The step reads only the typed text of the answer run's learner message, analyzes
    it outside any transaction and commits the memories, their change records and the
    analysis receipt together under the response fences. ``execute`` never raises: a
    failed analysis writes nothing and no receipt, so a retry may analyze again.
    """

    def __init__(
        self,
        database: IntelligenceDatabase,
        analyzer: LearnerMemoryAnalyzerProvider,
        similarity: LearnerMemorySimilarityProvider,
        access_provider: MentorAccessProvider,
        clock_provider: ClockProvider,
        identifier_provider: IdentifierProvider,
        update_threshold: float,
    ) -> None:
        self._database = database
        self._analyzer = analyzer
        self._similarity = similarity
        self._access_provider = access_provider
        self._clock_provider = clock_provider
        self._identifier_provider = identifier_provider
        self._update_threshold = update_threshold

    def execute(self, attempt_id: str, execution_owner: str) -> None:
        """Never raises; a failed analysis writes nothing and no receipt."""
        try:
            self._run(attempt_id, execution_owner)
        except Exception:  # noqa: BLE001 - the memory step must never fail the answer run.
            _logger.warning(
                'learner memories step failed category=%s', _Failure.UNEXPECTED.value
            )

    def _run(self, attempt_id: str, owner: str) -> None:
        pending = self._open(attempt_id, owner)
        if pending is None:
            return
        try:
            analysis = self._analyzer.analyze(pending.message.content)
        except Exception:  # noqa: BLE001 - analyzers can fail on private text.
            _logger.warning(
                'learner memories step failed category=%s',
                _Failure.ANALYSIS_FAILED.value,
            )
            return
        outcome = self._settle(pending, owner, analysis)
        if outcome is None:
            _logger.warning(
                'learner memories step failed category=%s sentences=%d statements=%d',
                _Failure.COMMIT_REJECTED.value,
                analysis.sentence_count,
                len(analysis.statements),
            )
            return
        _logger.info(
            'learner memories analyzed sentences=%d created=%d updated=%d discarded=%d',
            analysis.sentence_count,
            outcome.created,
            outcome.updated,
            outcome.discarded,
        )

    def _open(self, attempt_id: str, owner: str) -> _Pending | None:
        """Claim the attempt and load its learner message unless it was analyzed."""
        try:
            attempt = start_response_attempt(
                self._database,
                self._clock_provider,
                self._access_provider,
                attempt_id,
                owner,
            )
            if attempt is None:
                return None
            assert_response_access(self._access_provider, attempt)
            with self._database.transaction() as repositories:
                repositories.mentor_sessions.lock_session(
                    attempt.account_id, attempt.session_id
                )
                assert_response_current(
                    repositories, attempt, owner, self._clock_provider
                )
                message = repositories.mentor_messages.find_by_id(
                    attempt.account_id, attempt.session_id, attempt.learner_message_id
                )
                if (
                    message is None
                    or message.role is not MentorMessageRole.LEARNER
                    or repositories.mentor_messages.find_memory_analysis(message.id)
                    is not None
                ):
                    return None
        except Exception:  # noqa: BLE001 - a lost claim or access ends the step quietly.
            _logger.warning(
                'learner memories step failed category=%s',
                _Failure.ATTEMPT_UNAVAILABLE.value,
            )
            return None
        return _Pending(attempt=attempt, message=message)

    def _settle(
        self, pending: _Pending, owner: str, analysis: LearnerMemoryAnalysis
    ) -> _Outcome | None:
        """Write memories, change records and the receipt under the response fences."""
        attempt, message = pending.attempt, pending.message
        try:
            with self._database.transaction() as repositories:
                repositories.mentor_sessions.lock_session(
                    attempt.account_id, attempt.session_id
                )
                assert_response_current(
                    repositories, attempt, owner, self._clock_provider
                )
                assert_response_access(self._access_provider, attempt)
                statements = analysis.statements
                if statements:
                    fence = repositories.learner_memories.lock_account(
                        attempt.account_id
                    )
                    if fence is not None and message.created_at <= fence:
                        statements = ()
                outcome = self._apply(repositories, pending, statements)
                outcome.discarded += len(analysis.statements) - len(statements)
                # "Anotado" is only honest when every statement was recorded.
                repositories.mentor_messages.mark_memory_analyzed(
                    message.id,
                    self._clock_provider.now(),
                    analysis.statement_only and outcome.discarded == 0,
                )
                return outcome
        except Exception:  # noqa: BLE001 - fence failures write nothing and no receipt.
            return None

    def _apply(
        self,
        repositories: IntelligenceDatabaseRepositories,
        pending: _Pending,
        statements: tuple[LearnerMemoryStatement, ...],
    ) -> _Outcome:
        outcome = _Outcome()
        if not statements:
            return outcome
        memories = list(
            repositories.learner_memories.find_many_by_account(
                pending.attempt.account_id
            )
        )
        for statement in statements:
            kind = self._apply_statement(repositories, pending, memories, statement)
            if kind is LearnerMemoryChangeKind.CREATED:
                outcome.created += 1
            elif kind is LearnerMemoryChangeKind.UPDATED:
                outcome.updated += 1
            else:
                outcome.discarded += 1
        return outcome

    def _apply_statement(
        self,
        repositories: IntelligenceDatabaseRepositories,
        pending: _Pending,
        memories: list[LearnerMemory],
        statement: LearnerMemoryStatement,
    ) -> LearnerMemoryChangeKind | None:
        """Create, update or (for a stale declaration) discard one statement."""
        attempt, message = pending.attempt, pending.message
        now = self._clock_provider.now()
        origin = LearnerMemoryOrigin(
            session_id=attempt.session_id,
            message_id=message.id,
            declared_at=message.created_at,
        )
        best = self._best_match(memories, statement)
        if best is None:
            memory = LearnerMemory.create(
                id=self._identifier_provider.generate(),
                account_id=attempt.account_id,
                statement=statement,
                declared_at=message.created_at,
                now=now,
            )
            repositories.learner_memories.add(memory, statement.concepts, origin)
            memories.append(memory)
            kind, previous_content = LearnerMemoryChangeKind.CREATED, None
        else:
            previous_content = best.content
            if not best.apply_declaration(statement.content, message.created_at, now):
                return None
            repositories.learner_memories.update(best, statement.concepts)
            repositories.learner_memories.add_origin(best.id, origin)
            memory, kind = best, LearnerMemoryChangeKind.UPDATED
        repositories.learner_memory_changes.add(
            LearnerMemoryChange(
                id=self._identifier_provider.generate(),
                account_id=attempt.account_id,
                memory_id=memory.id,
                session_id=attempt.session_id,
                message_id=message.id,
                kind=kind,
                category=memory.category,
                content=memory.content,
                previous_content=previous_content,
                created_at=now,
            )
        )
        return kind

    def _best_match(
        self, memories: list[LearnerMemory], statement: LearnerMemoryStatement
    ) -> LearnerMemory | None:
        """The most similar memory of the same category at or above the threshold."""
        candidates = sorted(
            (memory for memory in memories if memory.category is statement.category),
            key=lambda memory: memory.id,
        )
        candidates.sort(key=lambda memory: memory.updated_at, reverse=True)
        best: LearnerMemory | None = None
        best_score = 0.0
        for memory in candidates:
            score = self._similarity.similarity(statement.content, memory.content)
            if best is None or score > best_score:
                best, best_score = memory, score
        if best is None or best_score < self._update_threshold:
            return None
        return best

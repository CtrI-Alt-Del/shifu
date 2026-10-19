from dataclasses import asdict, replace

from shifu.intelligence.core.domain.entities import MentorResponseAttempt
from shifu.intelligence.core.domain.enums import (
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import (
    MentorResponseBlock,
    MentorResponseSnapshot,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases.mentor_response_phase_helpers import (
    assert_response_access,
    response_event,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import MentorContextSnapshot
from shifu.shared.core.interfaces import (
    ClockProvider,
    MentorAccessProvider,
    MentorContextProvider,
)


class PublishMentorResponseBlockUseCase:
    """Publish one approved response block after revalidating its context."""

    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
        context_provider: MentorContextProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider
        self._access_provider = access_provider
        self._context_provider = context_provider

    def execute(
        self,
        attempt_id: str,
        execution_owner: str,
        block: MentorResponseBlock,
        expected_context: MentorContextSnapshot,
    ) -> bool:
        attempt = self._load_attempt(attempt_id)
        if attempt is None:
            return False
        assert_response_access(self._access_provider, attempt)
        fresh_context = self._context_provider.read(
            attempt.account_id,
            expected_context.resolved_references,
            **self._hints(attempt),
        )
        if self._context_permissions(fresh_context) != self._context_permissions(
            expected_context
        ):
            raise ServiceUnavailableError

        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id_for_update(
                attempt.account_id, attempt.session_id
            )
            current = repositories.mentor_response_attempts.find_by_id_for_update(
                attempt.id
            )
            latest = repositories.mentor_response_attempts.find_current(
                attempt.account_id, attempt.session_id
            )
            if (
                session is None
                or current is None
                or current.status is not MentorResponseStatus.PROCESSING
                or current.access_revision != attempt.access_revision
                or latest is None
                or latest.id != attempt.id
                or not repositories.mentor_response_attempts.has_claim(
                    attempt.id, execution_owner, self._clock_provider.now()
                )
            ):
                return False
            assert_response_access(self._access_provider, attempt)
            snapshot = repositories.mentor_response_events.snapshot(
                attempt.account_id, attempt.session_id
            )
            existing = self._existing_block(snapshot, block.block_key)
            if existing is not None:
                # The persisted event is authoritative when a workflow resumes
                # after a committed publication. Do not append a replayed
                # candidate or fail because its transient output differs.
                return True
            event = response_event(
                attempt,
                self._clock_provider,
                repositories.mentor_response_events.next_sequence(attempt.session_id),
                MentorResponseEventKind.BLOCK,
                MentorResponseStatus.PROCESSING,
            )
            repositories.mentor_response_events.append(replace(event, block=block))
            return True

    def _load_attempt(self, attempt_id: str) -> MentorResponseAttempt | None:
        with self._database.transaction() as repositories:
            return repositories.mentor_response_attempts.find_by_id(attempt_id)

    @staticmethod
    def _hints(attempt: MentorResponseAttempt) -> dict[str, str | None]:
        return asdict(attempt.context_hint) if attempt.context_hint else {}

    @staticmethod
    def _existing_block(
        snapshot: MentorResponseSnapshot | None, block_key: str
    ) -> MentorResponseBlock | None:
        if snapshot is None:
            return None
        return next(
            (block for block in snapshot.blocks if block.block_key == block_key), None
        )

    @staticmethod
    def _context_permissions(context: MentorContextSnapshot) -> tuple[object, ...]:
        return (
            context.goal_id,
            context.skill_experience_id,
            context.skill_id,
            context.activity_id,
            context.skill_completed,
            context.diagnostic_in_progress,
            context.eligible_references,
        )

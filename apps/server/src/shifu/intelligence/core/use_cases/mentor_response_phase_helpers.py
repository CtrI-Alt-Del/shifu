from dataclasses import replace
from datetime import timedelta

from shifu.intelligence.core.domain.entities import MentorResponseAttempt
from shifu.intelligence.core.domain.enums import (
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import MentorResponseEvent
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import (
    ClockProvider,
    MentorAccessProvider,
)


def assert_response_access(
    access_provider: MentorAccessProvider, attempt: MentorResponseAttempt
) -> None:
    access_provider.assert_current(
        MentorAccessGrant(
            account_id=attempt.account_id,
            access_revision=attempt.access_revision,
            operation_key=attempt.operation_key,
        )
    )


def assert_response_current(
    repositories: IntelligenceDatabaseRepositories,
    attempt: MentorResponseAttempt,
    execution_owner: str,
    clock_provider: ClockProvider,
) -> None:
    session = repositories.mentor_sessions.find_by_id_for_update(
        attempt.account_id, attempt.session_id
    )
    current = repositories.mentor_response_attempts.find_by_id(attempt.id)
    latest = repositories.mentor_response_attempts.find_current(
        attempt.account_id, attempt.session_id
    )
    now = clock_provider.now()
    if (
        session is None
        or current is None
        or current.status is not MentorResponseStatus.PROCESSING
        or current.access_revision != attempt.access_revision
        or latest is None
        or latest.id != attempt.id
        or not repositories.mentor_response_attempts.has_claim(
            attempt.id, execution_owner, now
        )
    ):
        raise ServiceUnavailableError


def response_event(
    attempt: MentorResponseAttempt,
    clock_provider: ClockProvider,
    sequence: int,
    kind: MentorResponseEventKind,
    status: MentorResponseStatus,
) -> MentorResponseEvent:
    return MentorResponseEvent(
        session_id=attempt.session_id,
        attempt_id=attempt.id,
        sequence=sequence,
        kind=kind,
        status=status,
        block=None,
        consultation=None,
        failure_code=None,
        created_at=clock_provider.now(),
    )


def claim_for_failure(
    repositories: IntelligenceDatabaseRepositories,
    attempt: MentorResponseAttempt,
    execution_owner: str,
    clock_provider: ClockProvider,
) -> bool:
    now = clock_provider.now()
    return repositories.mentor_response_attempts.has_claim(
        attempt.id, execution_owner, now
    ) or repositories.mentor_response_attempts.claim(
        attempt.id,
        execution_owner,
        now,
        now + timedelta(minutes=5),
        attempt.access_revision,
    )


def start_response_attempt(
    database: IntelligenceDatabase,
    clock_provider: ClockProvider,
    access_provider: MentorAccessProvider,
    attempt_id: str,
    execution_owner: str,
) -> MentorResponseAttempt | None:
    """Claim a queued/processing attempt for ``execution_owner`` and mark it processing.

    Returns ``None`` when the attempt is absent, finished, no longer the current one
    or claimed by another live owner. Re-claiming with the same owner is allowed.
    """
    with database.transaction() as repositories:
        attempt = repositories.mentor_response_attempts.find_by_id_for_update(
            attempt_id
        )
        if attempt is None or attempt.status not in (
            MentorResponseStatus.QUEUED,
            MentorResponseStatus.PROCESSING,
        ):
            return None
        session = repositories.mentor_sessions.find_by_id_for_update(
            attempt.account_id, attempt.session_id
        )
        current = repositories.mentor_response_attempts.find_current(
            attempt.account_id, attempt.session_id
        )
        now = clock_provider.now()
        if (
            session is None
            or current is None
            or current.id != attempt.id
            or not repositories.mentor_response_attempts.claim(
                attempt.id,
                execution_owner,
                now,
                now + timedelta(minutes=5),
                attempt.access_revision,
            )
        ):
            return None
    assert_response_access(access_provider, attempt)
    with database.transaction() as repositories:
        if not repositories.mentor_response_attempts.has_claim(
            attempt.id, execution_owner, clock_provider.now()
        ):
            raise ServiceUnavailableError
        assert_response_access(access_provider, attempt)
        if attempt.status is MentorResponseStatus.QUEUED:
            if not repositories.mentor_response_attempts.transition(
                attempt.id,
                MentorResponseStatus.QUEUED,
                MentorResponseStatus.PROCESSING,
                attempt.access_revision,
            ):
                return None
            sequence = repositories.mentor_response_events.next_sequence(
                attempt.session_id
            )
            repositories.mentor_response_events.append(
                response_event(
                    attempt,
                    clock_provider,
                    sequence,
                    MentorResponseEventKind.STATUS,
                    MentorResponseStatus.PROCESSING,
                )
            )
    return replace(attempt, status=MentorResponseStatus.PROCESSING)

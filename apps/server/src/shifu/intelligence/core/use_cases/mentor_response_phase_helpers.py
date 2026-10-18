from datetime import timedelta

from shifu.intelligence.core.domain.entities import MentorResponseAttempt
from shifu.intelligence.core.domain.enums import (
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import MentorResponseEvent
from shifu.intelligence.core.interfaces import IntelligenceDatabaseRepositories
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

from dataclasses import replace
from typing import Any

from shifu.intelligence.core.domain.enums import (
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases.mentor_response_phase_helpers import (
    assert_response_access,
    claim_for_failure,
    response_event,
)
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class FailMentorResponseUseCase:
    _FAILURE_CODES = frozenset({'service_unavailable'})

    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider
        self._access_provider = access_provider

    def execute(
        self,
        attempt_id: str,
        execution_owner: str,
        failure_code: str,
    ) -> MentorResponseStatus:
        failure_code_value: Any = failure_code
        if (
            not isinstance(failure_code_value, str)
            or failure_code_value not in self._FAILURE_CODES
        ):
            raise ValueError('Unsupported Mentor response failure code')
        with self._database.transaction() as repositories:
            attempt = repositories.mentor_response_attempts.find_by_id_for_update(
                attempt_id
            )
            if attempt is None:
                return MentorResponseStatus.CANCELLED
            session = repositories.mentor_sessions.find_by_id_for_update(
                attempt.account_id, attempt.session_id
            )
            current = repositories.mentor_response_attempts.find_by_id_for_update(
                attempt_id
            )
            latest = repositories.mentor_response_attempts.find_current(
                attempt.account_id, attempt.session_id
            )
            if session is None or current is None:
                return MentorResponseStatus.CANCELLED
            if current.status not in (
                MentorResponseStatus.QUEUED,
                MentorResponseStatus.PROCESSING,
            ):
                return current.status
            if latest is None or latest.id != current.id:
                return MentorResponseStatus.CANCELLED
            if not claim_for_failure(
                repositories, attempt, execution_owner, self._clock_provider
            ):
                return current.status
            if not repositories.mentor_response_attempts.transition(
                attempt_id,
                current.status,
                MentorResponseStatus.FAILED,
                attempt.access_revision,
            ):
                return current.status
            repositories.mentor_action_proposals.remove_pending_by_attempt_id(
                attempt.account_id, attempt_id
            )
            event = response_event(
                attempt,
                self._clock_provider,
                repositories.mentor_response_events.next_sequence(attempt.session_id),
                MentorResponseEventKind.FAILED,
                MentorResponseStatus.FAILED,
            )
            try:
                assert_response_access(self._access_provider, attempt)
            except Exception:  # noqa: BLE001 - failure state is closed without provider details
                return MentorResponseStatus.FAILED
            repositories.mentor_response_events.append(
                replace(event, failure_code=failure_code_value)
            )
            return MentorResponseStatus.FAILED

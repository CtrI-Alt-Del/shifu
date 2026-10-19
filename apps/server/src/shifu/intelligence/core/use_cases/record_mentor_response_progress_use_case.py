from dataclasses import replace

from shifu.intelligence.core.domain.enums import (
    MentorResponseEventKind,
    MentorResponseStatus,
    MentorWorkflowStep,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases.mentor_response_phase_helpers import (
    assert_response_access,
    response_event,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class RecordMentorResponseProgressUseCase:
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
        self, attempt_id: str, execution_owner: str, step: MentorWorkflowStep
    ) -> None:
        if type(step) is not MentorWorkflowStep:
            raise ServiceUnavailableError
        with self._database.transaction() as repositories:
            attempt = repositories.mentor_response_attempts.find_by_id_for_update(
                attempt_id
            )
            latest = (
                repositories.mentor_response_attempts.find_current(
                    attempt.account_id, attempt.session_id
                )
                if attempt is not None
                else None
            )
            if (
                attempt is None
                or attempt.status is not MentorResponseStatus.PROCESSING
                or latest is None
                or latest.id != attempt_id
                or not repositories.mentor_response_attempts.has_claim(
                    attempt_id, execution_owner, self._clock_provider.now()
                )
            ):
                raise ServiceUnavailableError
            assert_response_access(self._access_provider, attempt)
            event = response_event(
                attempt,
                self._clock_provider,
                repositories.mentor_response_events.next_sequence(attempt.session_id),
                MentorResponseEventKind.STATUS,
                MentorResponseStatus.PROCESSING,
            )
            repositories.mentor_response_events.append(replace(event, progress=step))

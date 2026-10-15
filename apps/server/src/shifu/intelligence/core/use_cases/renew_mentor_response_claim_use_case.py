from datetime import timedelta

from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases.mentor_response_phase_helpers import (
    assert_response_access,
)
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class RenewMentorResponseClaimUseCase:
    _CLAIM_DURATION = timedelta(minutes=5)

    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider
        self._access_provider = access_provider

    def execute(self, attempt_id: str, execution_owner: str) -> bool:
        with self._database.transaction() as repositories:
            attempt = repositories.mentor_response_attempts.find_by_id(attempt_id)
        if attempt is None:
            return False
        assert_response_access(self._access_provider, attempt)
        now = self._clock_provider.now()
        with self._database.transaction() as repositories:
            current = repositories.mentor_response_attempts.find_by_id_for_update(
                attempt_id
            )
            latest = repositories.mentor_response_attempts.find_current(
                attempt.account_id, attempt.session_id
            )
            if (
                current is None
                or current.status is not MentorResponseStatus.PROCESSING
                or current.access_revision != attempt.access_revision
                or latest is None
                or latest.id != attempt_id
                or not repositories.mentor_response_attempts.renew_claim(
                    attempt_id,
                    execution_owner,
                    now,
                    now + self._CLAIM_DURATION,
                    attempt.access_revision,
                )
            ):
                return False
        assert_response_access(self._access_provider, attempt)
        return True

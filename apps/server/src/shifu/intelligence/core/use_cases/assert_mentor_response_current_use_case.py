from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases.mentor_response_phase_helpers import (
    assert_response_access,
    assert_response_current,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class AssertMentorResponseCurrentUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider
        self._access_provider = access_provider

    def execute(self, attempt_id: str, execution_owner: str) -> None:
        with self._database.transaction() as repositories:
            attempt = repositories.mentor_response_attempts.find_by_id(attempt_id)
            if attempt is None:
                raise ServiceUnavailableError
            assert_response_current(
                repositories, attempt, execution_owner, self._clock_provider
            )
        assert_response_access(self._access_provider, attempt)

from typing import ClassVar

from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases.fail_mentor_response_use_case import (
    FailMentorResponseUseCase,
)


class FailStaleMentorResponseUseCase:
    """Fail the session's processing attempt when no live execution holds it.

    A worker that stops without closing its attempt leaves it processing, which
    blocks every new message of the conversation. The recovery owner can only claim
    an attempt whose claim is free or expired, so a live execution is never touched.
    """

    RECOVERY_OWNER: ClassVar[str] = 'stale-response-recovery'

    def __init__(
        self,
        database: IntelligenceDatabase,
        fail_use_case: FailMentorResponseUseCase,
    ) -> None:
        self._database: IntelligenceDatabase = database
        self._fail_use_case: FailMentorResponseUseCase = fail_use_case

    def execute(self, account_id: str, session_id: str) -> bool:
        with self._database.transaction() as repositories:
            current = repositories.mentor_response_attempts.find_current(
                account_id, session_id
            )
        if current is None or current.status is not MentorResponseStatus.PROCESSING:
            return False
        status = self._fail_use_case.execute(
            current.id, self.RECOVERY_OWNER, 'service_unavailable'
        )
        return status is MentorResponseStatus.FAILED

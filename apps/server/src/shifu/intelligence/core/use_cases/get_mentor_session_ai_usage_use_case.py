from decimal import ROUND_CEILING, Decimal

from shifu.intelligence.core.domain.errors import MentorSessionNotFoundError
from shifu.intelligence.core.domain.structures import (
    MentorMessageAiUsage,
    MentorSessionAiUsage,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import MentorAccessProvider

_HUNDREDTH = Decimal('0.01')


class GetMentorSessionAiUsageUseCase:
    """Read how much of the monthly AI quota each Mentor answer of a session spent."""

    def __init__(
        self, database: IntelligenceDatabase, access_provider: MentorAccessProvider
    ) -> None:
        self._database: IntelligenceDatabase = database
        self._access_provider: MentorAccessProvider = access_provider

    def execute(self, account_id: str, session_id: str) -> MentorSessionAiUsage:
        grant = self._access_provider.authorize(account_id, f'read:{session_id}')
        self._access_provider.assert_current(grant)
        # A short read without locks: the reading never blocks a charge.
        with self._database.transaction() as repositories:
            if repositories.mentor_sessions.find_by_id(account_id, session_id) is None:
                raise MentorSessionNotFoundError
            charges = repositories.ai_quota_charges.find_many_by_mentor_session(
                account_id, session_id
            )

        # The live answer is shown under its attempt, the stored one under its message.
        percentages: dict[tuple[str, str], Decimal] = {}
        for charge in charges:
            key = (charge.message_id, charge.attempt_id)
            share = Decimal(charge.charged_units * 100) / charge.limit_units
            percentages[key] = percentages.get(key, Decimal(0)) + share
        return MentorSessionAiUsage(
            items=tuple(
                MentorMessageAiUsage(
                    message_id=message_id,
                    attempt_id=attempt_id,
                    # Rounding up keeps any spent answer visible instead of showing 0%.
                    percentage=percentage.quantize(_HUNDREDTH, rounding=ROUND_CEILING),
                )
                for (message_id, attempt_id), percentage in percentages.items()
                if percentage > 0
            )
        )

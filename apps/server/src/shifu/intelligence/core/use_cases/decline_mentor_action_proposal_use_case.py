from shifu.intelligence.core.domain.errors import MentorSessionNotFoundError
from shifu.intelligence.core.domain.structures import MentorActionProposalItem
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases.mentor_detail import mentor_action_item
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class DeclineMentorActionProposalUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self._database: IntelligenceDatabase = database
        self._clock_provider: ClockProvider = clock_provider
        self._access_provider: MentorAccessProvider = access_provider

    def execute(
        self, account_id: str, session_id: str, proposal_id: str
    ) -> MentorActionProposalItem:
        grant = self._access_provider.authorize(
            account_id, f'action-proposal:decline:{proposal_id}'
        )
        self._access_provider.assert_current(grant)
        with self._database.transaction() as repositories:
            # The session lock serializes the decline with a new submission, which
            # checks for pending proposals under the same lock.
            session = repositories.mentor_sessions.find_by_id_for_update(
                account_id, session_id
            )
            if session is None:
                raise MentorSessionNotFoundError
            proposal = repositories.mentor_action_proposals.find_by_id_for_update(
                account_id, proposal_id
            )
            if proposal is None or proposal.session_id != session_id:
                raise MentorSessionNotFoundError
            proposal.decline(self._clock_provider.now())
            repositories.mentor_action_proposals.update(proposal)
            return mentor_action_item(proposal)

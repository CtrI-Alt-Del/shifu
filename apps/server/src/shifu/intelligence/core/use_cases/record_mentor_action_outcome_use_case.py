from typing import ClassVar

from shifu.intelligence.core.domain.entities import MentorActionProposal
from shifu.intelligence.core.domain.enums import (
    MentorActionKind,
    MentorActionProposalOutcome,
    MentorActionProposalRejectionReason,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import ClockProvider


class RecordMentorActionOutcomeUseCase:
    """Finalize a proposal from the Learning outcome the browser caused."""

    _REJECTED: ClassVar[str] = 'rejected'
    _SUCCESSES: ClassVar[
        dict[MentorActionKind, frozenset[MentorActionProposalOutcome]]
    ] = {
        MentorActionKind.ADD_SKILL: frozenset(
            {
                MentorActionProposalOutcome.ADDED,
                MentorActionProposalOutcome.ALREADY_PRESENT,
            }
        ),
        MentorActionKind.REMOVE_SKILL: frozenset({MentorActionProposalOutcome.REMOVED}),
    }

    def __init__(
        self, database: IntelligenceDatabase, clock_provider: ClockProvider
    ) -> None:
        self._database: IntelligenceDatabase = database
        self._clock_provider: ClockProvider = clock_provider

    def execute(
        self,
        account_id: str,
        confirmation_id: str,
        operation: str,
        outcome: str,
        rejection_reason: str | None,
        goal_id: str,
        skill_id: str | None,
        skill_experience_id: str | None,
    ) -> bool:
        """Return whether the proposal changed.

        The browser chose the confirmed values, so nothing changes unless they match
        what the proposal offered. Unknown ids, other accounts, mismatches and
        repeated deliveries are no-ops.
        """
        resolution = self._parse(operation, outcome, rejection_reason)
        if resolution is None:
            return False
        kind, parsed_outcome, parsed_reason = resolution
        with self._database.transaction() as repositories:
            proposal = repositories.mentor_action_proposals.find_by_id_for_update(
                account_id, confirmation_id
            )
            if proposal is None or not self._matches(
                proposal, kind, goal_id, skill_id, skill_experience_id
            ):
                return False
            if not proposal.resolve(
                parsed_outcome,
                parsed_reason,
                goal_id,
                skill_experience_id,
                self._clock_provider.now(),
            ):
                return False
            repositories.mentor_action_proposals.update(proposal)
            return True

    @classmethod
    def _parse(
        cls, operation: str, outcome: str, rejection_reason: str | None
    ) -> (
        tuple[
            MentorActionKind,
            MentorActionProposalOutcome | None,
            MentorActionProposalRejectionReason | None,
        ]
        | None
    ):
        try:
            kind = MentorActionKind(operation)
            if outcome == cls._REJECTED:
                if rejection_reason is None:
                    return None
                return kind, None, MentorActionProposalRejectionReason(rejection_reason)
            parsed = MentorActionProposalOutcome(outcome)
        except ValueError:
            return None
        if rejection_reason is not None or parsed not in cls._SUCCESSES[kind]:
            return None
        return kind, parsed, None

    @staticmethod
    def _matches(
        proposal: MentorActionProposal,
        kind: MentorActionKind,
        goal_id: str,
        skill_id: str | None,
        skill_experience_id: str | None,
    ) -> bool:
        if proposal.kind is not kind:
            return False
        if skill_id is not None and skill_id != proposal.skill_id:
            return False
        if proposal.goal_id is not None:
            fixed_experience = proposal.skill_experience_id
            return goal_id == proposal.goal_id and (
                kind is not MentorActionKind.REMOVE_SKILL
                or skill_experience_id == fixed_experience
            )
        candidate = next(
            (item for item in proposal.candidate_goals if item.goal_id == goal_id),
            None,
        )
        if candidate is None:
            return False
        return (
            kind is not MentorActionKind.REMOVE_SKILL
            or skill_experience_id == candidate.skill_experience_id
        )

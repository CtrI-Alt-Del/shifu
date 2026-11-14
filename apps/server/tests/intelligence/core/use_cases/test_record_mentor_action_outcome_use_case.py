from datetime import UTC, datetime
from typing import Any
from unittest.mock import create_autospec

import pytest

from shifu.fakers.intelligence.entities import MentorActionProposalFaker
from shifu.intelligence.core.domain.entities import MentorActionProposal
from shifu.intelligence.core.domain.enums import (
    MentorActionKind,
    MentorActionProposalOutcome,
    MentorActionProposalRejectionReason,
    MentorActionProposalStatus,
)
from shifu.intelligence.core.domain.structures import MentorActionCandidateGoal
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorActionProposalsRepository,
)
from shifu.intelligence.core.use_cases import RecordMentorActionOutcomeUseCase
from shifu.shared.core.interfaces import ClockProvider


class TestRecordMentorActionOutcomeUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.now = datetime(2026, 10, 10, tzinfo=UTC)
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.proposals = create_autospec(MentorActionProposalsRepository, instance=True)
        self.repositories.mentor_action_proposals = self.proposals
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = self.now
        self.subject = RecordMentorActionOutcomeUseCase(self.database, self.clock)
        self.addition = MentorActionProposalFaker.fake(
            id='proposal',
            account_id='account',
            skill_id='skill',
            goal_id='goal',
            goal_title='Aprender a programar',
        )
        self.removal = MentorActionProposalFaker.fake(
            id='proposal',
            account_id='account',
            kind=MentorActionKind.REMOVE_SKILL,
            skill_id='skill',
            goal_id='goal',
            goal_title='Aprender a programar',
            skill_experience_id='experience',
        )
        self.proposals.find_by_id_for_update.return_value = self.addition

    def _record(self, **changes: Any) -> bool:
        values: dict[str, Any] = {
            'account_id': 'account',
            'confirmation_id': 'proposal',
            'operation': 'add_skill',
            'outcome': 'added',
            'rejection_reason': None,
            'goal_id': 'goal',
            'skill_id': 'skill',
            'skill_experience_id': 'new-experience',
        }
        values.update(changes)
        return self.subject.execute(**values)

    def _use(self, proposal: MentorActionProposal) -> None:
        self.proposals.find_by_id_for_update.return_value = proposal

    @pytest.mark.parametrize(
        'outcome',
        [
            MentorActionProposalOutcome.ADDED,
            MentorActionProposalOutcome.ALREADY_PRESENT,
        ],
    )
    def test_should_complete_a_pending_addition(
        self, outcome: MentorActionProposalOutcome
    ) -> None:
        assert self._record(outcome=outcome.value) is True

        assert self.addition.status is MentorActionProposalStatus.COMPLETED
        assert self.addition.outcome is outcome
        assert self.addition.rejection_reason is None
        assert self.addition.resolved_goal_id == 'goal'
        assert self.addition.resolved_skill_experience_id == 'new-experience'
        assert self.addition.updated_at == self.now
        self.proposals.update.assert_called_once_with(self.addition)
        self.proposals.find_by_id_for_update.assert_called_once_with(
            'account', 'proposal'
        )

    def test_should_complete_a_pending_removal_of_the_fixed_experience(self) -> None:
        self._use(self.removal)

        assert (
            self._record(
                operation='remove_skill',
                outcome='removed',
                skill_experience_id='experience',
            )
            is True
        )

        assert self.removal.status is MentorActionProposalStatus.COMPLETED
        assert self.removal.outcome is MentorActionProposalOutcome.REMOVED
        assert self.removal.resolved_skill_experience_id == 'experience'

    @pytest.mark.parametrize('reason', list(MentorActionProposalRejectionReason))
    def test_should_reject_a_pending_proposal_with_the_reason(
        self, reason: MentorActionProposalRejectionReason
    ) -> None:
        assert (
            self._record(
                outcome='rejected',
                rejection_reason=reason.value,
                skill_experience_id=None,
            )
            is True
        )

        assert self.addition.status is MentorActionProposalStatus.REJECTED
        assert self.addition.outcome is None
        assert self.addition.rejection_reason is reason
        self.proposals.update.assert_called_once_with(self.addition)

    def test_should_let_an_outcome_replace_a_declined_proposal(self) -> None:
        self.addition.decline(self.now)

        assert self._record() is True

        assert self.addition.status is MentorActionProposalStatus.COMPLETED
        assert self.addition.outcome is MentorActionProposalOutcome.ADDED

    def test_should_ignore_a_repeated_delivery(self) -> None:
        assert self._record() is True
        self.proposals.update.reset_mock()

        assert self._record() is False

        self.proposals.update.assert_not_called()
        assert self.addition.status is MentorActionProposalStatus.COMPLETED

    def test_should_never_replace_a_final_outcome_with_another(self) -> None:
        assert self._record(outcome='added') is True
        self.proposals.update.reset_mock()

        assert self._record(outcome='already_present') is False
        assert (
            self._record(
                outcome='rejected',
                rejection_reason='goal_unavailable',
                skill_experience_id=None,
            )
            is False
        )

        self.proposals.update.assert_not_called()
        assert self.addition.outcome is MentorActionProposalOutcome.ADDED

    def test_should_ignore_an_unknown_proposal_or_another_account(self) -> None:
        self.proposals.find_by_id_for_update.return_value = None

        assert self._record(account_id='other-account') is False

        self.proposals.update.assert_not_called()
        self.proposals.find_by_id_for_update.assert_called_once_with(
            'other-account', 'proposal'
        )

    @pytest.mark.parametrize(
        'changes',
        [
            {'operation': 'remove_skill', 'outcome': 'removed'},
            {'skill_id': 'another-skill'},
            {'goal_id': 'another-goal'},
        ],
    )
    def test_should_ignore_values_the_addition_did_not_offer(
        self, changes: dict[str, str]
    ) -> None:
        assert self._record(**changes) is False

        self.proposals.update.assert_not_called()
        assert self.addition.status is MentorActionProposalStatus.PENDING

    @pytest.mark.parametrize(
        'changes',
        [
            {'skill_experience_id': 'another-experience'},
            {'skill_experience_id': None},
            {'goal_id': 'another-goal'},
            {'operation': 'add_skill', 'outcome': 'added'},
            {'skill_id': 'another-skill'},
        ],
    )
    def test_should_ignore_values_the_removal_did_not_offer(
        self, changes: dict[str, Any]
    ) -> None:
        self._use(self.removal)
        values: dict[str, Any] = {
            'operation': 'remove_skill',
            'outcome': 'removed',
            'skill_experience_id': 'experience',
        }
        values.update(changes)

        assert self._record(**values) is False

        self.proposals.update.assert_not_called()
        assert self.removal.status is MentorActionProposalStatus.PENDING

    def test_should_accept_the_chosen_candidate_of_an_open_destination(self) -> None:
        candidates = (
            MentorActionCandidateGoal(
                goal_id='goal-a',
                title='A',
                contains_skill=True,
                skill_experience_id='experience-a',
            ),
            MentorActionCandidateGoal(
                goal_id='goal-b',
                title='B',
                contains_skill=True,
                skill_experience_id='experience-b',
            ),
        )
        open_removal = MentorActionProposalFaker.fake(
            id='proposal',
            account_id='account',
            kind=MentorActionKind.REMOVE_SKILL,
            skill_id='skill',
            candidate_goals=candidates,
        )
        self._use(open_removal)

        assert (
            self._record(
                operation='remove_skill',
                outcome='removed',
                goal_id='goal-b',
                skill_experience_id='experience-a',
            )
            is False
        )
        assert (
            self._record(
                operation='remove_skill',
                outcome='removed',
                goal_id='goal-b',
                skill_experience_id='experience-b',
            )
            is True
        )

        assert open_removal.resolved_goal_id == 'goal-b'
        assert open_removal.resolved_skill_experience_id == 'experience-b'

    def test_should_ignore_a_goal_outside_the_candidates(self) -> None:
        open_addition = MentorActionProposalFaker.fake(
            id='proposal',
            account_id='account',
            skill_id='skill',
            candidate_goals=(
                MentorActionCandidateGoal(
                    goal_id='goal-a',
                    title='A',
                    contains_skill=False,
                    skill_experience_id=None,
                ),
            ),
        )
        self._use(open_addition)

        assert self._record(goal_id='goal-z') is False
        assert self._record(goal_id='goal-a') is True

    def test_should_accept_a_missing_skill_id_from_the_event(self) -> None:
        assert self._record(skill_id=None) is True

    @pytest.mark.parametrize(
        'changes',
        [
            {'operation': 'archive_skill'},
            {'outcome': 'unknown'},
            {'outcome': 'removed'},
            {'outcome': 'rejected', 'rejection_reason': None},
            {'outcome': 'rejected', 'rejection_reason': 'unknown'},
            {'rejection_reason': 'goal_unavailable'},
        ],
    )
    def test_should_ignore_values_outside_the_closed_sets(
        self, changes: dict[str, Any]
    ) -> None:
        assert self._record(**changes) is False

        self.database.transaction.assert_not_called()
        self.proposals.update.assert_not_called()

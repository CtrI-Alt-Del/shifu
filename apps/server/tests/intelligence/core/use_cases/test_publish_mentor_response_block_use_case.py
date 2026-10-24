from dataclasses import replace

import pytest
from shifu.intelligence.core.domain.enums import (
    MentorActionKind,
    MentorActionProposalStatus,
    MentorIntent,
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import (
    MentorActionCandidateGoal,
    MentorActionProposalDraft,
)
from shifu.intelligence.core.use_cases.publish_mentor_response_block_use_case import (
    PublishMentorResponseBlockUseCase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from tests.intelligence.core.use_cases.mentor_response_phase_test_setup import (
    MentorResponsePhaseTestSetup,
    context_snapshot,
)


class TestPublishMentorResponseBlockUseCase(MentorResponsePhaseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare_phase()
        self.identifiers.generate.side_effect = None
        self.identifiers.generate.return_value = 'proposal-id'
        self.subject = PublishMentorResponseBlockUseCase(
            self.database,
            self.clock,
            self.access,
            self.context_provider,
            self.identifiers,
        )
        self.action_block = replace(
            self.block,
            block_key='action-proposal',
            intent=MentorIntent.ADD_SKILL,
            content='Preparei uma proposta para você confirmar.',
        )
        self.draft = MentorActionProposalDraft(
            kind=MentorActionKind.ADD_SKILL,
            skill_id='skill',
            skill_name='Funções em Python',
            goal_id='goal',
            goal_title='Aprender a programar',
            skill_experience_id=None,
            candidate_goals=(),
            justification='Você pediu ao Mentor para adicionar esta Habilidade.',
        )

    def test_should_publish_approved_block_as_sequenced_event(self) -> None:
        assert self.subject.execute('attempt', 'owner', self.block, self.context)

        event = self.repositories.mentor_response_events.append.call_args.args[0]
        assert event.kind is MentorResponseEventKind.BLOCK
        assert event.status is MentorResponseStatus.PROCESSING
        assert event.sequence == 2
        assert event.block == self.block
        assert event.consultation is None
        assert event.failure_code is None

    def test_should_not_touch_proposals_when_publishing_a_plain_block(self) -> None:
        assert self.subject.execute('attempt', 'owner', self.block, self.context)

        self.repositories.mentor_action_proposals.add.assert_not_called()
        self.identifiers.generate.assert_not_called()

    def test_should_persist_proposal_and_action_event_beside_the_block(self) -> None:
        self.repositories.mentor_response_events.next_sequence.side_effect = [2, 3]

        assert self.subject.execute(
            'attempt',
            'owner',
            self.action_block,
            self.context,
            action_proposal=self.draft,
        )

        proposal = self.repositories.mentor_action_proposals.add.call_args.args[0]
        assert proposal.id == 'proposal-id'
        assert proposal.account_id == 'account'
        assert proposal.session_id == 'session'
        assert proposal.learner_message_id == 'message'
        assert proposal.attempt_id == 'attempt'
        assert proposal.kind is MentorActionKind.ADD_SKILL
        assert proposal.goal_id == 'goal'
        assert proposal.justification == self.draft.justification
        assert proposal.status is MentorActionProposalStatus.PENDING
        assert proposal.created_at == self.now
        block_event, action_event = (
            call.args[0]
            for call in self.repositories.mentor_response_events.append.call_args_list
        )
        assert block_event.kind is MentorResponseEventKind.BLOCK
        assert block_event.sequence == 2
        assert block_event.block == self.action_block
        assert block_event.action_proposal is None
        assert action_event.kind is MentorResponseEventKind.ACTION
        assert action_event.status is MentorResponseStatus.PROCESSING
        assert action_event.sequence == 3
        assert action_event.block is None
        assert action_event.action_proposal is not None
        assert action_event.action_proposal.id == 'proposal-id'
        assert action_event.action_proposal.source_message_id == 'message'
        assert action_event.action_proposal.status is MentorActionProposalStatus.PENDING
        self.database.transaction.assert_called()

    def test_should_keep_the_candidates_of_an_open_destination(self) -> None:
        candidate = MentorActionCandidateGoal(
            goal_id='goal-a',
            title='A',
            contains_skill=True,
            skill_experience_id='experience-a',
        )
        open_draft = MentorActionProposalDraft(
            kind=MentorActionKind.REMOVE_SKILL,
            skill_id='skill',
            skill_name='Funções em Python',
            goal_id=None,
            goal_title=None,
            skill_experience_id=None,
            candidate_goals=(candidate,),
            justification=None,
        )
        self.repositories.mentor_response_events.next_sequence.side_effect = [2, 3]

        assert self.subject.execute(
            'attempt',
            'owner',
            self.action_block,
            self.context,
            action_proposal=open_draft,
        )

        proposal = self.repositories.mentor_action_proposals.add.call_args.args[0]
        assert proposal.goal_id is None
        assert proposal.candidate_goals == (candidate,)
        action_event = self.repositories.mentor_response_events.append.call_args.args[0]
        assert action_event.action_proposal is not None
        assert action_event.action_proposal.candidate_goals == (candidate,)

    def test_should_not_duplicate_the_proposal_when_the_block_was_already_published(
        self,
    ) -> None:
        self.repositories.mentor_response_events.snapshot.return_value = replace(
            self.snapshot, blocks=(self.action_block,)
        )

        assert self.subject.execute(
            'attempt',
            'owner',
            self.action_block,
            self.context,
            action_proposal=self.draft,
        )

        self.repositories.mentor_action_proposals.add.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()

    def test_should_treat_a_previously_published_block_key_as_idempotent(self) -> None:
        persisted = replace(self.block, content='Persisted authoritative answer')
        self.repositories.mentor_response_events.snapshot.return_value = replace(
            self.snapshot, blocks=(persisted,)
        )

        assert self.subject.execute('attempt', 'owner', self.block, self.context)

        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_response_events.next_sequence.assert_not_called()

    def test_should_hide_missing_attempt_without_reading_context(self) -> None:
        self.repositories.mentor_response_attempts.find_by_id.return_value = None

        assert (
            self.subject.execute('missing', 'owner', self.block, self.context) is False
        )

        self.context_provider.read.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()

    def test_should_reject_changed_permissions_and_revoked_access(self) -> None:
        self.context_provider.read.return_value = context_snapshot(
            eligible_references=('new-reference',)
        )
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner', self.block, self.context)
        self.repositories.mentor_response_events.append.assert_not_called()

        self.context_provider.read.return_value = self.context
        self.access.assert_current.side_effect = ServiceUnavailableError()
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute(
                'attempt',
                'owner',
                self.action_block,
                self.context,
                action_proposal=self.draft,
            )
        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_action_proposals.add.assert_not_called()

    @pytest.mark.parametrize(
        'failure',
        (
            'missing-session',
            'missing-attempt',
            'not-processing',
            'stale-revision',
            'not-latest',
            'claim',
        ),
    )
    def test_should_not_publish_without_a_current_owned_processing_claim(
        self, failure: str
    ) -> None:
        if failure == 'missing-session':
            self.repositories.mentor_sessions.find_by_id_for_update.return_value = None
        elif failure == 'missing-attempt':
            self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = None
        elif failure == 'not-processing':
            self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
                self.attempt, status=MentorResponseStatus.CANCELLED
            )
        elif failure == 'stale-revision':
            self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
                self.attempt, access_revision='old-revision'
            )
        elif failure == 'not-latest':
            self.repositories.mentor_response_attempts.find_current.return_value = (
                replace(self.attempt, id='newer-attempt')
            )
        else:
            self.repositories.mentor_response_attempts.has_claim.return_value = False

        assert (
            self.subject.execute(
                'attempt',
                'owner',
                self.action_block,
                self.context,
                action_proposal=self.draft,
            )
            is False
        )

        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_action_proposals.add.assert_not_called()

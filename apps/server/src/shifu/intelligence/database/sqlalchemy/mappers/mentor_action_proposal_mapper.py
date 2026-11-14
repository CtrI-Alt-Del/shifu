from typing import cast

from shifu.intelligence.core.domain.entities import MentorActionProposal
from shifu.intelligence.core.domain.enums import (
    MentorActionKind,
    MentorActionProposalOutcome,
    MentorActionProposalRejectionReason,
    MentorActionProposalStatus,
)
from shifu.intelligence.core.domain.structures import (
    MentorActionCandidateGoal,
    MentorActionProposalItem,
)
from shifu.intelligence.database.sqlalchemy.models import MentorActionProposalModel


class MentorActionProposalMapper:
    @staticmethod
    def to_entity(model: MentorActionProposalModel) -> MentorActionProposal:
        return MentorActionProposal(
            id=model.id,
            account_id=model.account_id,
            session_id=model.session_id,
            learner_message_id=model.learner_message_id,
            attempt_id=model.attempt_id,
            kind=MentorActionKind(model.kind),
            skill_id=model.skill_id,
            skill_name=model.skill_name,
            goal_id=model.goal_id,
            goal_title=model.goal_title,
            skill_experience_id=model.skill_experience_id,
            candidate_goals=MentorActionProposalMapper._candidates(model),
            justification=model.justification,
            status=MentorActionProposalStatus(model.status),
            outcome=(
                MentorActionProposalOutcome(model.outcome)
                if model.outcome is not None
                else None
            ),
            rejection_reason=(
                MentorActionProposalRejectionReason(model.rejection_reason)
                if model.rejection_reason is not None
                else None
            ),
            resolved_goal_id=model.resolved_goal_id,
            resolved_skill_experience_id=model.resolved_skill_experience_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(proposal: MentorActionProposal) -> MentorActionProposalModel:
        model = MentorActionProposalModel(id=proposal.id)
        MentorActionProposalMapper.apply(model, proposal)
        return model

    @staticmethod
    def apply(model: MentorActionProposalModel, proposal: MentorActionProposal) -> None:
        """Copy the entity state onto its row (also used to update an existing row)."""
        model.account_id = proposal.account_id
        model.session_id = proposal.session_id
        model.learner_message_id = proposal.learner_message_id
        model.attempt_id = proposal.attempt_id
        model.kind = proposal.kind.value
        model.status = proposal.status.value
        model.outcome = proposal.outcome.value if proposal.outcome else None
        model.rejection_reason = (
            proposal.rejection_reason.value if proposal.rejection_reason else None
        )
        model.skill_id = proposal.skill_id
        model.skill_name = proposal.skill_name
        model.goal_id = proposal.goal_id
        model.goal_title = proposal.goal_title
        model.skill_experience_id = proposal.skill_experience_id
        model.candidate_goals = [
            {
                'goal_id': candidate.goal_id,
                'title': candidate.title,
                'contains_skill': candidate.contains_skill,
                'skill_experience_id': candidate.skill_experience_id,
            }
            for candidate in proposal.candidate_goals
        ]
        model.justification = proposal.justification
        model.resolved_goal_id = proposal.resolved_goal_id
        model.resolved_skill_experience_id = proposal.resolved_skill_experience_id
        model.created_at = proposal.created_at
        model.updated_at = proposal.updated_at

    @staticmethod
    def to_item(model: MentorActionProposalModel) -> MentorActionProposalItem:
        """Projection used when a response event is hydrated with the current state."""
        return MentorActionProposalItem(
            id=model.id,
            source_message_id=model.learner_message_id,
            kind=MentorActionKind(model.kind),
            skill_id=model.skill_id,
            skill_name=model.skill_name,
            goal_id=model.goal_id,
            goal_title=model.goal_title,
            skill_experience_id=model.skill_experience_id,
            candidate_goals=MentorActionProposalMapper._candidates(model),
            justification=model.justification,
            status=MentorActionProposalStatus(model.status),
            outcome=(
                MentorActionProposalOutcome(model.outcome)
                if model.outcome is not None
                else None
            ),
            rejection_reason=(
                MentorActionProposalRejectionReason(model.rejection_reason)
                if model.rejection_reason is not None
                else None
            ),
            resolved_goal_id=model.resolved_goal_id,
            resolved_skill_experience_id=model.resolved_skill_experience_id,
            created_at=model.created_at,
        )

    @staticmethod
    def _candidates(
        model: MentorActionProposalModel,
    ) -> tuple[MentorActionCandidateGoal, ...]:
        return tuple(
            MentorActionCandidateGoal(
                goal_id=cast('str', candidate['goal_id']),
                title=cast('str', candidate['title']),
                contains_skill=cast('bool', candidate['contains_skill']),
                skill_experience_id=cast(
                    'str | None', candidate['skill_experience_id']
                ),
            )
            for candidate in model.candidate_goals
        )

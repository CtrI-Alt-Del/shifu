from datetime import UTC, datetime

from faker import Faker

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.intelligence.core.domain.entities import MentorActionProposal
from shifu.intelligence.core.domain.enums import (
    MentorActionKind,
    MentorActionProposalOutcome,
    MentorActionProposalRejectionReason,
    MentorActionProposalStatus,
)
from shifu.intelligence.core.domain.structures import MentorActionCandidateGoal


class MentorActionProposalFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        session_id: str | None = None,
        learner_message_id: str | None = None,
        attempt_id: str | None = None,
        kind: MentorActionKind = MentorActionKind.ADD_SKILL,
        skill_id: str | None = None,
        skill_name: str | None = None,
        goal_id: str | None = None,
        goal_title: str | None = None,
        skill_experience_id: str | None = None,
        candidate_goals: tuple[MentorActionCandidateGoal, ...] = (),
        justification: str | None = None,
        status: MentorActionProposalStatus = MentorActionProposalStatus.PENDING,
        outcome: MentorActionProposalOutcome | None = None,
        rejection_reason: MentorActionProposalRejectionReason | None = None,
        resolved_goal_id: str | None = None,
        resolved_skill_experience_id: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> MentorActionProposal:
        """A pending proposal with a fixed destination unless candidates are given.

        An addition carries the default justification and a removal the experience
        it targets, so the default is always a valid proposal.
        """
        created = created_at or cls._faker.date_time(tzinfo=UTC)
        fixed = not candidate_goals
        resolved_goal = goal_id or (cls._id_provider.generate() if fixed else None)
        removal = kind is MentorActionKind.REMOVE_SKILL
        return MentorActionProposal(
            id=id or cls._id_provider.generate(),
            account_id=account_id or cls._id_provider.generate(),
            session_id=session_id or cls._id_provider.generate(),
            learner_message_id=learner_message_id or cls._id_provider.generate(),
            attempt_id=attempt_id or cls._id_provider.generate(),
            kind=kind,
            skill_id=skill_id or cls._id_provider.generate(),
            skill_name=skill_name or cls._faker.sentence(nb_words=3)[:255],
            goal_id=resolved_goal,
            goal_title=(
                goal_title or cls._faker.sentence(nb_words=3)[:255]
                if resolved_goal is not None
                else None
            ),
            skill_experience_id=skill_experience_id
            or (cls._id_provider.generate() if removal and fixed else None),
            candidate_goals=candidate_goals,
            justification=justification
            or (
                None
                if removal
                else 'Você pediu ao Mentor para adicionar esta Habilidade.'
            ),
            status=status,
            outcome=outcome,
            rejection_reason=rejection_reason,
            resolved_goal_id=resolved_goal_id,
            resolved_skill_experience_id=resolved_skill_experience_id,
            created_at=created,
            updated_at=updated_at or created,
        )

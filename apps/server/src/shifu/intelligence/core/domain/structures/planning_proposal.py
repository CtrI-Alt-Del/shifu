from shifu.intelligence.core.domain.structures.planning_proposal_skill import (
    PlanningProposalSkill,
)
from shifu.intelligence.core.domain.structures.planning_skill_relation import (
    PlanningSkillRelation,
)
from shifu.shared.core.domain.structures import structure


@structure
class PlanningProposal:
    title: str
    description: str
    skills: tuple[PlanningProposalSkill, ...]
    relations: tuple[PlanningSkillRelation, ...] = ()

    def __post_init__(self) -> None:
        if not self.title.strip() or not self.description.strip():
            raise ValueError('A proposal needs a title and a description.')
        if not self.skills:
            raise ValueError('A proposal needs at least one Skill.')
        identifiers = [skill.skill_id for skill in self.skills]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError('A proposal cannot repeat a Skill.')
        if len(set(self.relations)) != len(self.relations):
            raise ValueError('A proposal cannot repeat a relation.')
        known = set(identifiers)
        if any(
            relation.skill_id not in known or relation.foundation_skill_id not in known
            for relation in self.relations
        ):
            raise ValueError('Relations must connect proposed Skills only.')

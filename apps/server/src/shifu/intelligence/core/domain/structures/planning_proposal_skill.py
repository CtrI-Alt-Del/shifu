from shifu.shared.core.domain.structures import structure


@structure
class PlanningProposalSkill:
    skill_id: str
    name: str
    justification: str

    def __post_init__(self) -> None:
        if (
            not self.skill_id.strip()
            or not self.name.strip()
            or not self.justification.strip()
        ):
            raise ValueError(
                'A proposed Skill needs an id, a name and a justification.'
            )

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

MAX_SKILLS = 20


class PlanningProposalSkillOutput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    skill_id: str
    justification: str


class PlanningProposalOutput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    supported: bool
    title: str
    description: str
    skills: list[PlanningProposalSkillOutput]

    @model_validator(mode='after')
    def _bounded(self) -> Self:
        if len(self.skills) > MAX_SKILLS:
            raise ValueError('A proposal lists at most twenty Skills')
        return self

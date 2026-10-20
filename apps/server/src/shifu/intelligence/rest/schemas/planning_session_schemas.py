from datetime import datetime

from pydantic import BaseModel

from shifu.intelligence.core.domain.enums import (
    PlanningOperationKind,
    PlanningOperationStage,
    PlanningQuestionKind,
    PlanningSessionStatus,
)


class PlanningSessionSchemas:
    class Option(BaseModel):
        id: str
        text: str
        exclusive: bool

    class Question(BaseModel):
        id: str
        text: str
        kind: PlanningQuestionKind
        options: list['PlanningSessionSchemas.Option']

    class Batch(BaseModel):
        id: str
        questions: list['PlanningSessionSchemas.Question']

    class Operation(BaseModel):
        kind: PlanningOperationKind
        started_at: datetime
        stage: PlanningOperationStage | None

    class ProposalSkill(BaseModel):
        skill_id: str
        name: str
        justification: str

    class Relation(BaseModel):
        skill_id: str
        foundation_skill_id: str

    class Proposal(BaseModel):
        title: str
        description: str
        skills: list['PlanningSessionSchemas.ProposalSkill']
        relations: list['PlanningSessionSchemas.Relation']

    class Detail(BaseModel):
        id: str
        status: PlanningSessionStatus
        intent: str
        generation: int
        created_at: datetime
        updated_at: datetime
        operation: 'PlanningSessionSchemas.Operation | None'
        consulted_curriculum: bool
        batch: 'PlanningSessionSchemas.Batch | None'
        answered_batch_count: int
        proposal: 'PlanningSessionSchemas.Proposal | None'
        message: str | None
        failure_code: str | None

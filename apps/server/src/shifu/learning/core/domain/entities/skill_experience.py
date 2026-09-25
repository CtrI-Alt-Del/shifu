from datetime import datetime

from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.errors import SkillExperienceTransitionError
from shifu.learning.core.domain.structures import SkillCompletionSummary
from shifu.shared.core.domain.entities import entity


@entity
class SkillExperience:
    id: str
    goal_id: str
    skill_id: str
    inclusion_reason: str | None
    status: SkillExperienceStatus
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    completion_summary: SkillCompletionSummary | None = None
    policy_id: str = 'learning-v1'
    recommended_concept_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        id: str,
        goal_id: str,
        skill_id: str,
        inclusion_reason: str | None,
        status: SkillExperienceStatus,
        created_at: datetime,
        updated_at: datetime,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        completion_summary: SkillCompletionSummary | None = None,
        policy_id: str = 'learning-v1',
        recommended_concept_id: str | None = None,
    ) -> 'SkillExperience':
        return cls(
            id=id,
            goal_id=goal_id,
            skill_id=skill_id,
            inclusion_reason=inclusion_reason,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            started_at=started_at,
            completed_at=completed_at,
            completion_summary=completion_summary,
            policy_id=policy_id,
            recommended_concept_id=recommended_concept_id,
        )

    def start_diagnosis(self, started_at: datetime) -> None:
        if self.status is not SkillExperienceStatus.NOT_STARTED:
            raise SkillExperienceTransitionError
        self.status = SkillExperienceStatus.DIAGNOSING
        self.started_at = self.started_at or started_at
        self.updated_at = started_at

    def start_learning(self, updated_at: datetime) -> None:
        if self.status is not SkillExperienceStatus.DIAGNOSING:
            raise SkillExperienceTransitionError
        self.status = SkillExperienceStatus.LEARNING
        self.updated_at = updated_at

    def complete(
        self,
        summary: SkillCompletionSummary,
        completed_at: datetime,
    ) -> None:
        if self.status not in {
            SkillExperienceStatus.DIAGNOSING,
            SkillExperienceStatus.LEARNING,
        }:
            raise SkillExperienceTransitionError
        self.status = SkillExperienceStatus.COMPLETED
        self.completed_at = self.completed_at or completed_at
        self.completion_summary = self.completion_summary or summary
        self.updated_at = completed_at

    @property
    def accepts_progress_updates(self) -> bool:
        return self.status is not SkillExperienceStatus.COMPLETED

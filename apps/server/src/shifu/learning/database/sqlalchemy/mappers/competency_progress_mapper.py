from shifu.learning.core.domain.entities import CompetencyProgress
from shifu.learning.core.domain.enums import CompetencyProgressStatus
from shifu.learning.database.sqlalchemy.models import CompetencyProgressModel


class CompetencyProgressMapper:
    @staticmethod
    def to_domain(model: CompetencyProgressModel) -> CompetencyProgress:
        return CompetencyProgress(
            id=model.id,
            skill_experience_id=model.skill_experience_id,
            competency_id=model.competency_id,
            content_released=model.content_released,
            created_at=model.created_at,
            updated_at=model.updated_at,
            initial_progress=model.initial_progress,
            current_progress=model.current_progress,
            hard_activity_score=model.hard_activity_score,
            status=(
                CompetencyProgressStatus(model.status)
                if model.status is not None
                else None
            ),
            mastered_at=model.mastered_at,
            coverage_complete=model.coverage_complete,
            verification_cause=model.verification_cause,
            verification_concept_id=model.verification_concept_id,
        )

    @staticmethod
    def to_model(progress: CompetencyProgress) -> CompetencyProgressModel:
        return CompetencyProgressModel(
            id=progress.id,
            skill_experience_id=progress.skill_experience_id,
            competency_id=progress.competency_id,
            content_released=progress.content_released,
            created_at=progress.created_at,
            updated_at=progress.updated_at,
            initial_progress=progress.initial_progress,
            current_progress=progress.current_progress,
            hard_activity_score=progress.hard_activity_score,
            status=progress.status.value if progress.status is not None else None,
            mastered_at=progress.mastered_at,
            coverage_complete=progress.coverage_complete,
            verification_cause=progress.verification_cause,
            verification_concept_id=progress.verification_concept_id,
        )

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
            status=(
                CompetencyProgressStatus(model.status)
                if model.status is not None
                else None
            ),
            mastered_at=model.mastered_at,
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
            status=progress.status.value if progress.status is not None else None,
            mastered_at=progress.mastered_at,
        )

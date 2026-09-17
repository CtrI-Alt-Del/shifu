from typing import cast

from shifu.learning.core.domain.entities import SkillExperience
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.structures import SkillCompletionSummary
from shifu.learning.database.sqlalchemy.models import SkillExperienceModel
from shifu.shared.database.sqlalchemy.serialization import Serialization


class SkillExperienceMapper:
    @staticmethod
    def to_domain(model: SkillExperienceModel) -> SkillExperience:
        return SkillExperience(
            id=model.id,
            goal_id=model.goal_id,
            skill_id=model.skill_id,
            inclusion_reason=model.inclusion_reason,
            status=SkillExperienceStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            completion_summary=(
                cast(
                    'SkillCompletionSummary',
                    Serialization.deserialize_value(
                        model.completion_summary, SkillCompletionSummary
                    ),
                )
                if model.completion_summary is not None
                else None
            ),
        )

    @staticmethod
    def to_model(experience: SkillExperience) -> SkillExperienceModel:
        return SkillExperienceModel(
            id=experience.id,
            goal_id=experience.goal_id,
            skill_id=experience.skill_id,
            inclusion_reason=experience.inclusion_reason,
            status=experience.status.value,
            created_at=experience.created_at,
            updated_at=experience.updated_at,
            started_at=experience.started_at,
            completed_at=experience.completed_at,
            completion_summary=(
                Serialization.serialize_value(experience.completion_summary)
                if experience.completion_summary is not None
                else None
            ),
        )

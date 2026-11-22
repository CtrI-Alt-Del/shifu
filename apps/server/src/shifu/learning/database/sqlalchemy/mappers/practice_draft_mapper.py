from shifu.learning.core.domain.entities.practice_draft import PracticeDraft
from shifu.learning.core.domain.enums import PracticeDraftStatus
from shifu.learning.database.sqlalchemy.models import PracticeDraftModel


class PracticeDraftMapper:
    @staticmethod
    def to_domain(model: PracticeDraftModel) -> PracticeDraft:
        return PracticeDraft(
            id=model.id,
            skill_experience_id=model.skill_experience_id,
            activity_id=model.activity_id,
            reflection=model.reflection,
            revision=model.revision,
            status=PracticeDraftStatus(model.status),
        )

    @staticmethod
    def to_model(draft: PracticeDraft) -> PracticeDraftModel:
        return PracticeDraftModel(
            id=draft.id,
            skill_experience_id=draft.skill_experience_id,
            activity_id=draft.activity_id,
            reflection=draft.reflection,
            revision=draft.revision,
            status=draft.status.value,
        )

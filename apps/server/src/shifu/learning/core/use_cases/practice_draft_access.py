from shifu.learning.core.domain.entities import (
    PracticeDraft,
    PracticePhoto,
    SkillExperience,
)
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.structures import PracticeDraftView, PracticePhotoView
from shifu.learning.core.interfaces import LearningDatabaseRepositories
from shifu.shared.core.domain.errors import ConflictError, NotFoundError
from shifu.shared.core.domain.structures import (
    CurriculumPracticalPreparationQuestionSnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider


class PracticeDraftAccess:
    """Resolve ownership, release and rubric records for private practice drafts."""

    def __init__(self, curriculum_content_provider: CurriculumContentProvider) -> None:
        self._curriculum_content_provider = curriculum_content_provider

    def record_keys(self, activity_id: str, competency_id: str) -> frozenset[str]:
        snapshot = self._curriculum_content_provider.get_learning_activity(activity_id)
        if (
            snapshot is None
            or snapshot.id != activity_id
            or snapshot.competency_id != competency_id
            or snapshot.activity_type != 'learning'
        ):
            raise NotFoundError

        for question in snapshot.questions:
            if isinstance(question, CurriculumPracticalPreparationQuestionSnapshot):
                return frozenset(record.key for record in question.records)

        raise NotFoundError

    @staticmethod
    def locate(
        repositories: LearningDatabaseRepositories,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        *,
        for_update: bool,
    ) -> SkillExperience:
        goal = repositories.goals.find_by_id(goal_id)
        if goal is None or goal.id != goal_id or goal.account_id != account_id:
            raise NotFoundError

        experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
            goal_id, skill_id
        )
        if (
            experience is None
            or experience.goal_id != goal_id
            or experience.skill_id != skill_id
        ):
            raise NotFoundError

        if for_update:
            experience = repositories.skill_experiences.find_by_id_for_update(
                experience.id
            )
            if experience is None:
                raise NotFoundError

        progress = repositories.competency_progresses.find_by_skill_experience_id_and_competency_id(
            experience.id, competency_id
        )
        if (
            experience.status
            not in {SkillExperienceStatus.LEARNING, SkillExperienceStatus.COMPLETED}
            or progress is None
            or progress.skill_experience_id != experience.id
            or progress.competency_id != competency_id
            or not progress.content_released
        ):
            raise NotFoundError

        return experience

    @staticmethod
    def assert_writable(
        repositories: LearningDatabaseRepositories, experience: SkillExperience
    ) -> None:
        unresolved = (
            repositories.activity_evaluations.find_unresolved_by_skill_experience_id(
                experience.id
            )
        )
        if unresolved is not None:
            raise ConflictError

    @staticmethod
    def view(
        draft: PracticeDraft | None, photos: tuple[PracticePhoto, ...]
    ) -> PracticeDraftView:
        if draft is None:
            return PracticeDraftView(revision=0, reflection='', photos=())

        return PracticeDraftView(
            revision=draft.revision,
            reflection=draft.reflection,
            photos=tuple(
                PracticePhotoView(
                    record_key=photo.record_key,
                    photo_id=photo.id,
                    state=photo.state,
                    media_type=photo.media_type,
                    size_bytes=photo.size_bytes,
                )
                for photo in photos
            ),
        )

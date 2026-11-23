from shifu.learning.core.domain.enums import PracticePhotoOwnerKind, PracticePhotoState
from shifu.learning.core.domain.structures import PracticePhotoContent
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.errors import NotFoundError
from shifu.shared.core.interfaces import FileStorageProvider


class GetPracticeAttemptPhotoUseCase:
    """Read a photo owned by a submitted attempt; only the account that owns it may."""

    def __init__(
        self,
        learning_database: LearningDatabase,
        storage_provider: FileStorageProvider,
    ) -> None:
        self._learning_database = learning_database
        self._storage_provider = storage_provider

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        attempt_id: str,
        photo_id: str,
    ) -> PracticePhotoContent:
        with self._learning_database.transaction() as repositories:
            goal = repositories.goals.find_by_id(goal_id)
            if goal is None or goal.id != goal_id or goal.account_id != account_id:
                raise NotFoundError

            experience = repositories.skill_experiences.find_by_goal_id_and_skill_id(
                goal_id, skill_id
            )
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            if (
                experience is None
                or experience.goal_id != goal_id
                or experience.skill_id != skill_id
                or attempt is None
                or attempt.skill_experience_id != experience.id
                or attempt.competency_id != competency_id
                or attempt.activity_id != activity_id
            ):
                raise NotFoundError

            photo = repositories.practice_photos.find_by_id(photo_id)
            if (
                photo is None
                or photo.owner_kind is not PracticePhotoOwnerKind.ATTEMPT
                or photo.attempt_id != attempt_id
                or photo.state is not PracticePhotoState.READY
            ):
                raise NotFoundError

        content = self._storage_provider.read(photo.object_key)
        return PracticePhotoContent(media_type=photo.media_type, content=content)

from shifu.learning.core.domain.entities import PracticeDraft, PracticePhoto
from shifu.learning.core.domain.enums import PracticePhotoOwnerKind, PracticePhotoState
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.practice_photo_object_key import (
    PracticePhotoObjectKey,
)
from shifu.shared.core.interfaces import FileStorageProvider


class PurgePracticePhotosUseCase:
    """Delete private practice photo objects outside the database transaction."""

    def __init__(
        self,
        learning_database: LearningDatabase,
        storage_provider: FileStorageProvider,
    ) -> None:
        self._learning_database = learning_database
        self._storage_provider = storage_provider

    def execute(self, photo_id: str, object_key: str) -> bool:
        """Delete the object of a removed or failed photo and clear its mark.

        Returns False without touching storage when a live draft photo or an attempt
        still owns the object. A missing row means its owner was removed, so the
        orphan object is deleted.
        """
        if not PracticePhotoObjectKey.matches(photo_id, object_key):
            raise InvalidAttemptError

        with self._learning_database.transaction() as repositories:
            photo = repositories.practice_photos.find_by_id(photo_id)
            if photo is not None and not self._is_releasable(photo):
                return False

        self._storage_provider.remove(object_key)

        with self._learning_database.transaction() as repositories:
            current = repositories.practice_photos.find_by_id(photo_id)
            if current is not None and current.state is PracticePhotoState.REMOVED:
                repositories.practice_photos.remove(photo_id)
        return True

    def execute_for_deleted_account(self, account_id: str) -> int:
        """Delete every draft, photo row and object left for a closed account."""
        if not account_id.strip():
            raise InvalidAttemptError

        drafts: list[PracticeDraft] = []
        photos: list[PracticePhoto] = []
        with self._learning_database.transaction() as repositories:
            for goal in repositories.goals.find_many_by_account_id(account_id):
                for experience in repositories.skill_experiences.find_many_by_goal_id(
                    goal.id
                ):
                    drafts.extend(
                        repositories.practice_drafts.find_many_by_skill_experience_id(
                            experience.id
                        )
                    )
                    photos.extend(
                        repositories.practice_photos.list_for_skill_experience(
                            experience.id
                        )
                    )

        for photo in photos:
            self._storage_provider.remove(photo.object_key)

        with self._learning_database.transaction() as repositories:
            for photo in photos:
                repositories.practice_photos.remove(photo.id)
            for draft in drafts:
                repositories.practice_drafts.remove(draft.id)
        return len(photos)

    @staticmethod
    def _is_releasable(photo: PracticePhoto) -> bool:
        return photo.owner_kind is PracticePhotoOwnerKind.DRAFT and photo.state in {
            PracticePhotoState.REMOVED,
            PracticePhotoState.FAILED,
        }

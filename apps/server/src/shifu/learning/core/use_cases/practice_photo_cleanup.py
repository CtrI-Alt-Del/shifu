from shifu.learning.core.domain.entities import PracticePhoto
from shifu.learning.core.domain.events import (
    PracticePhotoCleanupRequestedEvent,
    PracticePhotoCleanupRequestedPayload,
)
from shifu.learning.core.interfaces import LearningDatabaseRepositories


class PracticePhotoCleanup:
    """Persist object cleanup requests inside the calling transaction."""

    @staticmethod
    def request(
        repositories: LearningDatabaseRepositories, photo_id: str, object_key: str
    ) -> None:
        repositories.events.add(
            PracticePhotoCleanupRequestedEvent(
                payload=PracticePhotoCleanupRequestedPayload(
                    photo_id=photo_id, object_key=object_key
                )
            )
        )

    @staticmethod
    def request_for_photos(
        repositories: LearningDatabaseRepositories,
        photos: tuple[PracticePhoto, ...],
    ) -> None:
        for photo in photos:
            PracticePhotoCleanup.request(repositories, photo.id, photo.object_key)

    @staticmethod
    def request_for_skill_experience(
        repositories: LearningDatabaseRepositories, skill_experience_id: str
    ) -> None:
        """Queue cleanup for every draft and attempt photo before rows disappear."""
        PracticePhotoCleanup.request_for_photos(
            repositories,
            repositories.practice_photos.list_for_skill_experience(skill_experience_id),
        )

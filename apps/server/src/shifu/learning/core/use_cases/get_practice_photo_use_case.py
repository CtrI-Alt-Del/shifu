from shifu.learning.core.domain.enums import PracticePhotoOwnerKind, PracticePhotoState
from shifu.learning.core.domain.structures import PracticePhotoContent
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.practice_draft_access import PracticeDraftAccess
from shifu.shared.core.domain.errors import NotFoundError
from shifu.shared.core.interfaces import CurriculumContentProvider, FileStorageProvider


class GetPracticePhotoUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        storage_provider: FileStorageProvider,
    ) -> None:
        self._learning_database = learning_database
        self._access = PracticeDraftAccess(curriculum_content_provider)
        self._storage_provider = storage_provider

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        record_key: str,
    ) -> PracticePhotoContent:
        if record_key not in self._access.record_keys(activity_id, competency_id):
            raise NotFoundError

        with self._learning_database.transaction() as repositories:
            experience = PracticeDraftAccess.locate(
                repositories,
                account_id,
                goal_id,
                skill_id,
                competency_id,
                for_update=False,
            )
            draft = repositories.practice_drafts.find_active(experience.id, activity_id)
            photo = (
                repositories.practice_photos.find_live_for_record(draft.id, record_key)
                if draft is not None
                else None
            )
            if (
                photo is None
                or photo.owner_kind is not PracticePhotoOwnerKind.DRAFT
                or photo.state is not PracticePhotoState.READY
            ):
                raise NotFoundError

        content = self._storage_provider.read(photo.object_key)
        return PracticePhotoContent(media_type=photo.media_type, content=content)

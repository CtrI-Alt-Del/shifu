from shifu.learning.core.domain.structures import PracticeDraftView
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.practice_draft_access import PracticeDraftAccess
from shifu.learning.core.use_cases.practice_photo_cleanup import PracticePhotoCleanup
from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider


class RemovePracticePhotoUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        clock_provider: ClockProvider,
    ) -> None:
        self._learning_database = learning_database
        self._access = PracticeDraftAccess(curriculum_content_provider)
        self._clock_provider = clock_provider

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        record_key: str,
    ) -> PracticeDraftView:
        if record_key not in self._access.record_keys(activity_id, competency_id):
            raise ValidationError

        now = self._clock_provider.now()
        with self._learning_database.transaction() as repositories:
            experience = PracticeDraftAccess.locate(
                repositories,
                account_id,
                goal_id,
                skill_id,
                competency_id,
                for_update=True,
            )
            PracticeDraftAccess.assert_writable(repositories, experience)
            draft = repositories.practice_drafts.find_active_for_update(
                experience.id, activity_id
            )
            if draft is None:
                return PracticeDraftAccess.view(None, ())

            photo = repositories.practice_photos.find_live_for_record(
                draft.id, record_key
            )
            if photo is not None:
                photo.mark_removed(now)
                repositories.practice_photos.update(photo)
                PracticePhotoCleanup.request(repositories, photo.id, photo.object_key)
                draft.bump_revision()
                repositories.practice_drafts.update(draft)

            return PracticeDraftAccess.view(
                draft, repositories.practice_photos.list_live_for_draft(draft.id)
            )

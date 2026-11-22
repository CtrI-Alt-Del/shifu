from shifu.learning.core.domain.structures import PracticeDraftView
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.practice_draft_access import PracticeDraftAccess
from shifu.shared.core.interfaces import CurriculumContentProvider


class GetPracticeDraftUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
    ) -> None:
        self._learning_database = learning_database
        self._access = PracticeDraftAccess(curriculum_content_provider)

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
    ) -> PracticeDraftView:
        self._access.record_keys(activity_id, competency_id)
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
            photos = (
                repositories.practice_photos.list_live_for_draft(draft.id)
                if draft is not None
                else ()
            )
            return PracticeDraftAccess.view(draft, photos)

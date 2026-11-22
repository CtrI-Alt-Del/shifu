from shifu.learning.core.domain.entities import PracticeDraft
from shifu.learning.core.domain.structures import PracticeDraftView
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.practice_draft_access import PracticeDraftAccess
from shifu.shared.core.interfaces import CurriculumContentProvider, IdentifierProvider


class SavePracticeReflectionUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        identifier_provider: IdentifierProvider,
    ) -> None:
        self._learning_database = learning_database
        self._access = PracticeDraftAccess(curriculum_content_provider)
        self._identifier_provider = identifier_provider

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        reflection: str,
    ) -> PracticeDraftView:
        self._access.record_keys(activity_id, competency_id)
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
            is_new = draft is None
            if draft is None:
                draft = PracticeDraft.create(
                    id=self._identifier_provider.generate(),
                    skill_experience_id=experience.id,
                    activity_id=activity_id,
                )

            draft.write_reflection(reflection)
            if is_new:
                repositories.practice_drafts.add(draft)
            else:
                repositories.practice_drafts.update(draft)

            return PracticeDraftAccess.view(
                draft, repositories.practice_photos.list_live_for_draft(draft.id)
            )

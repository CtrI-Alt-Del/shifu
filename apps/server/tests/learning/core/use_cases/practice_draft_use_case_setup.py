"""Shared arrangement for the private practice draft and photo use case tests."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import create_autospec

from shifu.fakers.learning.entities import (
    CompetencyProgressFaker,
    GoalFaker,
    SkillExperienceFaker,
)
from shifu.fakers.shared.curriculum_practical_preparation_question_snapshot_faker import (
    CurriculumPracticalPreparationQuestionSnapshotFaker,
)
from shifu.learning.core.domain.entities import PracticeDraft, PracticePhoto
from shifu.learning.core.domain.enums import (
    PracticeDraftStatus,
    PracticePhotoState,
    SkillExperienceStatus,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.shared.core.domain.structures import (
    CurriculumChoicePartSnapshot,
    CurriculumLearningActivitySnapshot,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)

ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
SKILL_ID = 'skill-1'
COMPETENCY_ID = 'competency-1'
ACTIVITY_ID = 'activity-1'
EXPERIENCE_ID = 'experience-1'
NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


def practical_snapshot(
    *, activity_type: str = 'learning'
) -> CurriculumLearningActivitySnapshot:
    return CurriculumLearningActivitySnapshot(
        id=ACTIVITY_ID,
        competency_id=COMPETENCY_ID,
        difficulty='easy',
        title='Legumes salteados',
        questions=(CurriculumPracticalPreparationQuestionSnapshotFaker.fake(),),
        parts=(
            CurriculumChoicePartSnapshot(
                question_key='sauteed-vegetables', weight_percentage=Decimal(100)
            ),
        ),
        required_concept_ids=(),
        activity_type=activity_type,
        schema_version=1,
        revision='revision-1',
    )


def fake_draft(
    *, revision: int = 0, status: PracticeDraftStatus = PracticeDraftStatus.ACTIVE
) -> PracticeDraft:
    draft = PracticeDraft.create(
        id='draft-1', skill_experience_id=EXPERIENCE_ID, activity_id=ACTIVITY_ID
    )
    draft.revision = revision
    draft.status = status
    return draft


def fake_photo(
    *,
    photo_id: str = 'photo-1',
    record_key: str = 'cuts',
    state: PracticePhotoState = PracticePhotoState.READY,
    upload_key: str = '8b3a3f4e-2f1c-4c52-9d0b-1c2d3e4f5a6b',
    sha256: str = 'a' * 64,
) -> PracticePhoto:
    photo = PracticePhoto.create(
        id=photo_id,
        draft_id='draft-1',
        record_key=record_key,
        object_key=f'practice-photos/{photo_id}/original',
        media_type='image/jpeg',
        size_bytes=100,
        sha256=sha256,
        upload_key=upload_key,
    )
    photo.state = state
    return photo


class PracticeDraftUseCaseSetup:
    """Mocked Learning boundary with an owned, released practical Activity."""

    def __init__(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.curriculum = create_autospec(CurriculumContentProvider, instance=True)
        self.curriculum.get_learning_activity.return_value = practical_snapshot()
        self.identifiers = create_autospec(IdentifierProvider, instance=True)
        self.identifiers.generate.side_effect = ['generated-1', 'generated-2']
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.experience = SkillExperienceFaker.fake(
            id=EXPERIENCE_ID,
            goal_id=GOAL_ID,
            skill_id=SKILL_ID,
            status=SkillExperienceStatus.LEARNING,
        )
        self.repositories.goals.find_by_id.return_value = GoalFaker.fake(
            id=GOAL_ID, account_id=ACCOUNT_ID
        )
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.experience
        self.repositories.skill_experiences.find_by_id_for_update.return_value = (
            self.experience
        )
        self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value = CompetencyProgressFaker.fake(
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            content_released=True,
        )
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = None
        self.repositories.practice_drafts.find_active.return_value = None
        self.repositories.practice_drafts.find_active_for_update.return_value = None
        self.repositories.practice_photos.list_live_for_draft.return_value = ()
        self.repositories.practice_photos.find_live_for_record.return_value = None
        self.repositories.practice_photos.find_by_upload_key.return_value = None

    @property
    def scope(self) -> tuple[str, str, str, str, str]:
        return ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID

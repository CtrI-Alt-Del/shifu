"""The private result of a practical preparation attempt, its photos and its retry."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    CompetencyProgress,
    PracticePhoto,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
    PracticePhotoOwnerKind,
    PracticePhotoState,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures import (
    ChoiceAttemptDetail,
    PracticalConceptEvidence,
    PracticalCriterionResult,
    PracticalPreparationAnswer,
    PracticalPreparationResult,
    PracticalPreparationResultDetail,
    PracticePhotoContent,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import (
    GetChoiceAttemptUseCase,
    GetPracticeAttemptPhotoUseCase,
    RetryChoiceEvaluationUseCase,
)
from shifu.shared.core.domain.errors import ConflictError, NotFoundError
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    FileStorageProvider,
    IdentifierProvider,
)
from tests.learning.core.use_cases.practice_draft_use_case_setup import (
    ACCOUNT_ID,
    ACTIVITY_ID,
    COMPETENCY_ID,
    EXPERIENCE_ID,
    GOAL_ID,
    SKILL_ID,
    practical_snapshot,
)

NOW = datetime(2026, 11, 21, 12, tzinfo=UTC)
ATTEMPT_ID = 'attempt-1'
QUESTION_KEY = 'sauteed-vegetables'


def attempt_photo(
    photo_id: str, record_key: str, state: PracticePhotoState = PracticePhotoState.READY
) -> PracticePhoto:
    return PracticePhoto(
        id=photo_id,
        owner_kind=PracticePhotoOwnerKind.ATTEMPT,
        draft_id=None,
        attempt_id=ATTEMPT_ID,
        record_key=record_key,
        object_key=f'practice-photos/{photo_id}/original',
        media_type='image/png',
        size_bytes=10,
        sha256='a' * 64,
        state=state,
        upload_key=f'upload-{photo_id}',
        removal_due_at=None,
    )


PHOTOS = (
    attempt_photo('photo-1', 'cuts'),
    attempt_photo('photo-2', 'during'),
    attempt_photo('photo-3', 'final'),
)


def find_photo(photo_id: str) -> PracticePhoto | None:
    return next((item for item in PHOTOS if item.id == photo_id), None)


def graded_result() -> PracticalPreparationResult:
    return PracticalPreparationResult(
        question_key=QUESTION_KEY,
        score=Decimal(60),
        closed_without_grade=False,
        criterion_results=(
            PracticalCriterionResult(
                criterion_key='cut-regularity',
                level=100,
                comment_key='cut-regularity-100',
            ),
            PracticalCriterionResult(
                criterion_key='observable-technique',
                level=50,
                comment_key='observable-technique-50',
            ),
            PracticalCriterionResult(
                criterion_key='presentation', level=0, comment_key='presentation-0'
            ),
        ),
        unassessable_record_keys=(),
        concept_evidence=(PracticalConceptEvidence(concept_id='c', value=Decimal(60)),),
    )


def closed_result() -> PracticalPreparationResult:
    return PracticalPreparationResult(
        question_key=QUESTION_KEY,
        score=None,
        closed_without_grade=True,
        criterion_results=(
            PracticalCriterionResult(
                criterion_key='cut-regularity', level=None, comment_key=None
            ),
            PracticalCriterionResult(
                criterion_key='observable-technique',
                level=75,
                comment_key='observable-technique-75',
            ),
            PracticalCriterionResult(
                criterion_key='presentation', level=50, comment_key='presentation-50'
            ),
        ),
        unassessable_record_keys=('cuts',),
        concept_evidence=(PracticalConceptEvidence(concept_id='c', value=None),),
    )


class TestGetPracticalPreparationAttemptUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.curriculum = create_autospec(CurriculumContentProvider, instance=True)
        self.storage = create_autospec(FileStorageProvider, instance=True)
        self.storage.read.return_value = b'png-bytes'
        self.experience = SkillExperienceFaker.fake(
            id=EXPERIENCE_ID,
            goal_id=GOAL_ID,
            skill_id=SKILL_ID,
            status=SkillExperienceStatus.LEARNING,
        )
        self.attempt = ActivityAttempt.create(
            id=ATTEMPT_ID,
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(
                PracticalPreparationAnswer(
                    question_key=QUESTION_KEY,
                    draft_revision=4,
                    reflection='Achei difícil manter o fogo alto.',
                ),
            ),
            submitted_at=NOW - timedelta(minutes=1),
            submission_key='submission-1',
            grading_snapshot=practical_snapshot(),
        )
        self.evaluation = ActivityEvaluation.create(
            id='evaluation-1',
            attempt_id=ATTEMPT_ID,
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=NOW - timedelta(minutes=1),
            run_id='run-1',
        )
        repositories = self.repositories
        repositories.goals.find_by_id.return_value = GoalFaker.fake(
            id=GOAL_ID, account_id=ACCOUNT_ID
        )
        repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = (
            self.experience
        )
        repositories.skill_experiences.find_by_id_for_update.return_value = (
            self.experience
        )
        repositories.activity_attempts.find_by_id.return_value = self.attempt
        repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            self.attempt
        ]
        repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = (
            self.evaluation
        )
        repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [
            self.evaluation
        ]
        repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value = CompetencyProgress(
            id='progress-1',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            content_released=True,
            created_at=NOW,
            updated_at=NOW,
            initial_progress=Decimal(0),
            current_progress=Decimal(0),
            status=CompetencyProgressStatus.LEARNING,
        )
        repositories.practice_photos.list_for_attempt.return_value = PHOTOS
        repositories.practice_photos.find_by_id.side_effect = find_photo
        self.subject = GetChoiceAttemptUseCase(
            self.database, self.curriculum, self.clock
        )

    def _read(self) -> ChoiceAttemptDetail:
        return self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, ATTEMPT_ID
        )

    def _practical(self) -> PracticalPreparationResultDetail:
        (detail,) = self._read().questions
        assert isinstance(detail, PracticalPreparationResultDetail)
        return detail

    def _complete(self, result: PracticalPreparationResult) -> None:
        self.evaluation.status = ActivityEvaluationStatus.COMPLETED
        self.evaluation.score = Decimal(60)
        self.evaluation.completed_at = NOW
        self.evaluation.parts = (result,)

    def _close(self, result: PracticalPreparationResult) -> None:
        self.evaluation.close_without_grade(NOW, (result,))

    def test_should_show_each_criterion_with_weight_level_and_predefined_comment(
        self,
    ) -> None:
        self._complete(graded_result())

        detail = self._read()

        assert detail.status is ActivityEvaluationStatus.COMPLETED
        assert detail.score == Decimal(60)
        practical = self._practical()
        assert practical.closed_without_grade is False
        assert practical.guidance is None
        assert [
            (item.key, item.weight, item.level, item.comment)
            for item in practical.criteria
        ] == [
            (
                'cut-regularity',
                Decimal(40),
                100,
                'Regularidade dos cortes: nível 100 observável nas fotos.',
            ),
            (
                'observable-technique',
                Decimal(40),
                50,
                'Técnica observável: nível 50 observável nas fotos.',
            ),
            (
                'presentation',
                Decimal(20),
                0,
                'Apresentação: nível 0 observável nas fotos.',
            ),
        ]

    def test_should_show_the_frozen_records_photos_and_reflection_read_only(
        self,
    ) -> None:
        self._complete(graded_result())

        practical = self._practical()

        assert practical.reflection == 'Achei difícil manter o fogo alto.'
        assert [(item.record_key, item.photo_id) for item in practical.photos] == [
            ('cuts', 'photo-1'),
            ('during', 'photo-2'),
            ('final', 'photo-3'),
        ]
        assert [item.label for item in practical.records] == [
            'Cortes',
            'Durante o preparo',
            'Prato final',
        ]

    def test_should_show_a_closed_attempt_as_no_grade_with_guidance(self) -> None:
        self._close(closed_result())

        detail = self._read()

        assert detail.status is ActivityEvaluationStatus.CLOSED_WITHOUT_GRADE
        assert detail.score is None
        assert detail.retry_allowed is False
        assert detail.progress_after is None
        practical = self._practical()
        assert practical.closed_without_grade is True
        assert practical.score is None
        assert (
            practical.guidance
            == 'Refaça a foto dos cortes com os legumes bem visíveis.'
        )
        assert [
            (item.key, item.label, item.comment)
            for item in practical.unassessable_records
        ] == [
            (
                'cuts',
                'Cortes',
                'Refaça a foto dos cortes com os legumes bem visíveis.',
            )
        ]
        cut = practical.criteria[0]
        assert (cut.level, cut.comment) == (None, None)
        assert practical.criteria[1].level == 75
        assert practical.reflection == 'Achei difícil manter o fogo alto.'
        assert len(practical.photos) == 3

    def test_should_show_a_pending_attempt_with_photos_and_no_levels(self) -> None:
        detail = self._read()

        assert detail.status is ActivityEvaluationStatus.PENDING
        practical = self._practical()
        assert practical.closed_without_grade is False
        assert all(item.level is None for item in practical.criteria)
        assert len(practical.photos) == 3
        assert practical.reflection == 'Achei difícil manter o fogo alto.'

    def test_should_show_a_failed_attempt_as_recoverable(self) -> None:
        self.evaluation.fail('evaluation_failed')

        detail = self._read()

        assert detail.status is ActivityEvaluationStatus.FAILED
        assert detail.retry_allowed is True
        assert detail.score is None
        assert all(item.level is None for item in self._practical().criteria)

    def test_should_not_offer_a_retry_for_a_closed_attempt(self) -> None:
        self._close(closed_result())
        subject = RetryChoiceEvaluationUseCase(
            self.database,
            self.clock,
            create_autospec(IdentifierProvider, instance=True),
        )

        with pytest.raises(ConflictError):
            subject.execute(
                ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, ATTEMPT_ID
            )

        assert self.evaluation.status is ActivityEvaluationStatus.CLOSED_WITHOUT_GRADE
        self.repositories.events.add.assert_not_called()

    def test_should_retry_the_same_failed_attempt_without_a_new_submission(
        self,
    ) -> None:
        self.evaluation.fail('evaluation_failed')
        identifiers = create_autospec(IdentifierProvider, instance=True)
        identifiers.generate.return_value = 'run-2'
        subject = RetryChoiceEvaluationUseCase(self.database, self.clock, identifiers)

        outcome = subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID, ATTEMPT_ID
        )

        assert outcome.status is ActivityEvaluationStatus.PENDING
        assert outcome.attempt_id == ATTEMPT_ID
        assert self.evaluation.run_id == 'run-2'
        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.practice_photos.reassign_to_attempt.assert_not_called()


class TestGetPracticeAttemptPhotoUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.storage = create_autospec(FileStorageProvider, instance=True)
        self.storage.read.return_value = b'png-bytes'
        experience = SkillExperienceFaker.fake(
            id=EXPERIENCE_ID, goal_id=GOAL_ID, skill_id=SKILL_ID
        )
        self.repositories.goals.find_by_id.return_value = GoalFaker.fake(
            id=GOAL_ID, account_id=ACCOUNT_ID
        )
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = experience
        self.repositories.activity_attempts.find_by_id.return_value = (
            ActivityAttempt.create(
                id=ATTEMPT_ID,
                skill_experience_id=EXPERIENCE_ID,
                competency_id=COMPETENCY_ID,
                activity_id=ACTIVITY_ID,
                kind=ActivityAttemptKind.LEARNING,
                answers=(),
                submitted_at=NOW,
            )
        )
        self.repositories.practice_photos.find_by_id.side_effect = find_photo
        self.subject = GetPracticeAttemptPhotoUseCase(self.database, self.storage)

    def _read(
        self, *, account_id: str = ACCOUNT_ID, photo_id: str = 'photo-1'
    ) -> PracticePhotoContent:
        return self.subject.execute(
            account_id,
            GOAL_ID,
            SKILL_ID,
            COMPETENCY_ID,
            ACTIVITY_ID,
            ATTEMPT_ID,
            photo_id,
        )

    def test_should_return_the_bytes_of_an_attempt_photo_to_its_owner(self) -> None:
        content = self._read()

        assert content.media_type == 'image/png'
        assert content.content == b'png-bytes'
        self.storage.read.assert_called_once_with('practice-photos/photo-1/original')

    def test_should_deny_another_account(self) -> None:
        with pytest.raises(NotFoundError):
            self._read(account_id='someone-else')

        self.storage.read.assert_not_called()

    def test_should_not_find_a_photo_that_is_not_of_the_attempt(self) -> None:
        self.repositories.practice_photos.find_by_id.side_effect = None
        self.repositories.practice_photos.find_by_id.return_value = PracticePhoto(
            id='photo-9',
            owner_kind=PracticePhotoOwnerKind.ATTEMPT,
            draft_id=None,
            attempt_id='attempt-other',
            record_key='cuts',
            object_key='practice-photos/photo-9/original',
            media_type='image/png',
            size_bytes=10,
            sha256='a' * 64,
            state=PracticePhotoState.READY,
            upload_key='upload-9',
            removal_due_at=None,
        )

        with pytest.raises(NotFoundError):
            self._read(photo_id='photo-9')

        self.storage.read.assert_not_called()

    def test_should_not_find_an_unknown_photo(self) -> None:
        with pytest.raises(NotFoundError):
            self._read(photo_id='photo-404')

    def test_should_not_find_a_draft_photo_through_the_attempt_route(self) -> None:
        draft_photo = PracticePhoto.create(
            id='photo-d',
            draft_id='draft-1',
            record_key='cuts',
            object_key='practice-photos/photo-d/original',
            media_type='image/png',
            size_bytes=10,
            sha256='a' * 64,
            upload_key='upload-d',
        )
        draft_photo.mark_ready()
        self.repositories.practice_photos.find_by_id.side_effect = None
        self.repositories.practice_photos.find_by_id.return_value = draft_photo

        with pytest.raises(NotFoundError):
            self._read(photo_id='photo-d')

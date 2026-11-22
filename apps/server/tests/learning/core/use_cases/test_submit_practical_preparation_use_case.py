"""Submitting a practical preparation answer against the private practice draft."""

import pytest

from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    PracticePhoto,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    PracticeDraftStatus,
    PracticePhotoState,
)
from shifu.learning.core.domain.errors import (
    PracticeDraftConflictError,
    PracticeDraftIncompleteError,
)
from shifu.learning.core.domain.events.activity_submission_requested_event import (
    ActivitySubmissionRequestedEvent,
)
from shifu.learning.core.domain.structures import (
    ChoiceAnswerSubmission,
    ChoiceSubmissionOutcome,
    PracticalPreparationAnswer,
    PracticalPreparationAnswerSubmission,
)
from shifu.learning.core.use_cases import SubmitChoiceActivityUseCase
from shifu.shared.core.domain.errors import ConflictError, ValidationError
from tests.learning.core.use_cases.practice_draft_use_case_setup import (
    ACCOUNT_ID,
    ACTIVITY_ID,
    COMPETENCY_ID,
    EXPERIENCE_ID,
    GOAL_ID,
    NOW,
    SKILL_ID,
    PracticeDraftUseCaseSetup,
    fake_draft,
    fake_photo,
)

SUBMISSION_KEY = '3f2504e0-4f89-41d3-9a0d-0305e82c3301'
QUESTION_KEY = 'sauteed-vegetables'


def submission(revision: int = 3) -> tuple[PracticalPreparationAnswerSubmission, ...]:
    return (
        PracticalPreparationAnswerSubmission(
            question_key=QUESTION_KEY, draft_revision=revision
        ),
    )


def ready_photos() -> tuple[PracticePhoto, ...]:
    return (
        fake_photo(photo_id='photo-1', record_key='cuts', upload_key='key-1'),
        fake_photo(photo_id='photo-2', record_key='during', upload_key='key-2'),
        fake_photo(photo_id='photo-3', record_key='final', upload_key='key-3'),
    )


class TestSubmitPracticalPreparationUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.arrangement = PracticeDraftUseCaseSetup()
        self.repositories = self.arrangement.repositories
        self.arrangement.identifiers.generate.side_effect = [
            'attempt-1',
            'evaluation-1',
            'run-1',
        ]
        self.repositories.activity_attempts.find_by_skill_experience_id_and_submission_key.return_value = None
        self.repositories.ordering_passages.find_active.return_value = None
        self.draft = fake_draft(revision=3)
        self.draft.reflection = 'Cortei em cubos pequenos.'
        self.repositories.practice_drafts.find_active_for_update.return_value = (
            self.draft
        )
        self.repositories.practice_photos.list_live_for_draft.return_value = (
            ready_photos()
        )
        self.subject = SubmitChoiceActivityUseCase(
            self.arrangement.database,
            self.arrangement.curriculum,
            self.arrangement.clock,
            self.arrangement.identifiers,
        )

    def _submit(
        self,
        answers: tuple[
            PracticalPreparationAnswerSubmission | ChoiceAnswerSubmission, ...
        ]
        | None = None,
    ) -> ChoiceSubmissionOutcome:
        return self.subject.execute(
            ACCOUNT_ID,
            GOAL_ID,
            SKILL_ID,
            COMPETENCY_ID,
            ACTIVITY_ID,
            SUBMISSION_KEY,
            answers if answers is not None else submission(),
            'revision-1',
        )

    def test_should_create_one_pending_attempt_with_the_frozen_reflection(
        self,
    ) -> None:
        outcome = self._submit()

        assert outcome.replayed is False
        assert outcome.attempt.status is ActivityEvaluationStatus.PENDING
        attempt = self.repositories.activity_attempts.add.call_args.args[0]
        assert isinstance(attempt, ActivityAttempt)
        assert attempt.kind is ActivityAttemptKind.LEARNING
        assert attempt.skill_experience_id == EXPERIENCE_ID
        assert attempt.answers == (
            PracticalPreparationAnswer(
                question_key=QUESTION_KEY,
                draft_revision=3,
                reflection='Cortei em cubos pequenos.',
            ),
        )
        evaluation = self.repositories.activity_evaluations.add.call_args.args[0]
        assert isinstance(evaluation, ActivityEvaluation)
        assert evaluation.status is ActivityEvaluationStatus.PENDING
        assert evaluation.run_id == 'run-1'
        event = self.repositories.events.add.call_args.args[0]
        assert isinstance(event, ActivitySubmissionRequestedEvent)
        assert event.payload.attempt_id == 'attempt-1'
        assert self.repositories.events.add.call_count == 1

    def test_should_hand_the_photos_to_the_attempt_and_close_the_draft(self) -> None:
        self._submit()

        self.repositories.practice_photos.reassign_to_attempt.assert_called_once_with(
            self.draft.id, 'attempt-1'
        )
        assert self.draft.status is PracticeDraftStatus.CONSUMED
        self.repositories.practice_drafts.update.assert_called_once_with(self.draft)

    def test_should_submit_with_an_empty_reflection(self) -> None:
        self.draft.reflection = ''

        self._submit()

        attempt = self.repositories.activity_attempts.add.call_args.args[0]
        assert attempt.answers[0].reflection == ''

    def test_should_refuse_a_stale_draft_revision_without_side_effects(self) -> None:
        with pytest.raises(PracticeDraftConflictError):
            self._submit(submission(revision=2))

        self._assert_nothing_created()

    def test_should_refuse_when_the_draft_is_already_closed(self) -> None:
        self.repositories.practice_drafts.find_active_for_update.return_value = None

        with pytest.raises(PracticeDraftConflictError):
            self._submit()

        self._assert_nothing_created()

    def test_should_refuse_when_a_record_has_no_ready_photo(self) -> None:
        self.repositories.practice_photos.list_live_for_draft.return_value = (
            ready_photos()[:2]
        )

        with pytest.raises(PracticeDraftIncompleteError):
            self._submit()

        self._assert_nothing_created()

    def test_should_refuse_when_a_photo_is_still_uploading(self) -> None:
        photos = list(ready_photos())
        uploading = fake_photo(
            photo_id='photo-4',
            record_key='final',
            state=PracticePhotoState.UPLOADING,
            upload_key='key-4',
        )
        self.repositories.practice_photos.list_live_for_draft.return_value = (
            *photos[:2],
            uploading,
        )

        with pytest.raises(PracticeDraftIncompleteError):
            self._submit()

        self._assert_nothing_created()

    def test_should_refuse_a_failed_photo_as_a_missing_record(self) -> None:
        failed = fake_photo(
            photo_id='photo-4',
            record_key='final',
            state=PracticePhotoState.FAILED,
            upload_key='key-4',
        )
        self.repositories.practice_photos.list_live_for_draft.return_value = (
            *ready_photos()[:2],
            failed,
        )

        with pytest.raises(PracticeDraftIncompleteError):
            self._submit()

        self._assert_nothing_created()

    def test_should_refuse_while_another_evaluation_is_unresolved(self) -> None:
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = ActivityEvaluation.create(
            id='evaluation-0',
            attempt_id='attempt-0',
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=NOW,
            run_id='run-0',
        )

        with pytest.raises(ConflictError):
            self._submit()

        self._assert_nothing_created()

    def test_should_refuse_an_answer_of_another_kind(self) -> None:
        with pytest.raises(ValidationError):
            self._submit(
                (
                    ChoiceAnswerSubmission(
                        question_key=QUESTION_KEY, selected_option_keys=('a',)
                    ),
                )
            )

        self._assert_nothing_created()

    def test_should_refuse_a_negative_draft_revision(self) -> None:
        with pytest.raises(ValidationError):
            self._submit(submission(revision=-1))

        self._assert_nothing_created()

    def test_should_replay_the_same_submission_key_without_a_second_attempt(
        self,
    ) -> None:
        self._submit()
        created = self.repositories.activity_attempts.add.call_args.args[0]
        self.repositories.activity_attempts.add.reset_mock()
        self.repositories.activity_attempts.find_by_skill_experience_id_and_submission_key.return_value = created
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = (
            self.repositories.activity_evaluations.add.call_args.args[0]
        )

        replayed = self._submit()

        assert replayed.replayed is True
        assert replayed.attempt.attempt_id == created.id
        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.practice_photos.reassign_to_attempt.assert_called_once()

    def test_should_refuse_a_replay_that_carries_another_revision(self) -> None:
        self._submit()
        created = self.repositories.activity_attempts.add.call_args.args[0]
        self.repositories.activity_attempts.find_by_skill_experience_id_and_submission_key.return_value = created
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = (
            self.repositories.activity_evaluations.add.call_args.args[0]
        )

        with pytest.raises(ConflictError):
            self._submit(submission(revision=9))

    def _assert_nothing_created(self) -> None:
        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.activity_evaluations.add.assert_not_called()
        self.repositories.events.add.assert_not_called()
        self.repositories.practice_photos.reassign_to_attempt.assert_not_called()
        self.repositories.practice_drafts.update.assert_not_called()
        assert self.draft.status is PracticeDraftStatus.ACTIVE

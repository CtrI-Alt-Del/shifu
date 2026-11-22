import pytest

from shifu.fakers.learning.entities import ActivityEvaluationFaker
from shifu.learning.core.domain.enums import PracticePhotoState
from shifu.learning.core.domain.events import PracticePhotoCleanupRequestedEvent
from shifu.learning.core.use_cases import RemovePracticePhotoUseCase
from shifu.shared.core.domain.errors import ConflictError, ValidationError
from tests.learning.core.use_cases.practice_draft_use_case_setup import (
    NOW,
    PracticeDraftUseCaseSetup,
    fake_draft,
    fake_photo,
)


class TestRemovePracticePhotoUseCase:
    def setup_method(self) -> None:
        self.setup = PracticeDraftUseCaseSetup()
        self.repositories = self.setup.repositories
        self.subject = RemovePracticePhotoUseCase(
            self.setup.database, self.setup.curriculum, self.setup.clock
        )

    def test_should_mark_the_photo_removed_request_cleanup_and_grow_the_revision(
        self,
    ) -> None:
        draft = fake_draft(revision=5)
        photo = fake_photo()
        self.repositories.practice_drafts.find_active_for_update.return_value = draft
        self.repositories.practice_photos.find_live_for_record.return_value = photo
        self.repositories.practice_photos.list_live_for_draft.return_value = ()

        view = self.subject.execute(*self.setup.scope, 'cuts')

        assert photo.state is PracticePhotoState.REMOVED
        assert photo.removal_due_at is not None
        assert photo.removal_due_at > NOW
        self.repositories.practice_photos.update.assert_called_once_with(photo)
        event = self.repositories.events.add.call_args.args[0]
        assert isinstance(event, PracticePhotoCleanupRequestedEvent)
        assert event.payload.photo_id == photo.id
        assert (view.revision, view.photos) == (6, ())

    def test_should_return_the_current_view_when_the_record_has_no_photo(self) -> None:
        self.repositories.practice_drafts.find_active_for_update.return_value = (
            fake_draft(revision=2)
        )

        view = self.subject.execute(*self.setup.scope, 'cuts')

        assert view.revision == 2
        self.repositories.events.add.assert_not_called()

    def test_should_return_an_empty_view_without_a_draft(self) -> None:
        view = self.subject.execute(*self.setup.scope, 'cuts')

        assert (view.revision, view.photos) == (0, ())
        self.repositories.events.add.assert_not_called()

    def test_should_reject_a_record_the_activity_does_not_request(self) -> None:
        with pytest.raises(ValidationError):
            self.subject.execute(*self.setup.scope, 'unknown')

    def test_should_refuse_the_removal_while_an_evaluation_is_unresolved(self) -> None:
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = ActivityEvaluationFaker.fake()

        with pytest.raises(ConflictError):
            self.subject.execute(*self.setup.scope, 'cuts')

        self.repositories.practice_photos.update.assert_not_called()

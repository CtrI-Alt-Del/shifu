import pytest

from shifu.fakers.learning.entities import GoalFaker
from shifu.learning.core.domain.enums import PracticePhotoState
from shifu.learning.core.use_cases import GetPracticeDraftUseCase
from shifu.shared.core.domain.errors import NotFoundError
from tests.learning.core.use_cases.practice_draft_use_case_setup import (
    PracticeDraftUseCaseSetup,
    fake_draft,
    fake_photo,
)


class TestGetPracticeDraftUseCase:
    def setup_method(self) -> None:
        self.setup = PracticeDraftUseCaseSetup()
        self.subject = GetPracticeDraftUseCase(
            self.setup.database, self.setup.curriculum
        )

    def test_should_return_an_empty_view_without_creating_a_draft(self) -> None:
        view = self.subject.execute(*self.setup.scope)

        assert (view.revision, view.reflection, view.photos) == (0, '', ())
        self.setup.repositories.practice_drafts.add.assert_not_called()

    def test_should_return_the_saved_reflection_revision_and_photo_states(
        self,
    ) -> None:
        draft = fake_draft(revision=4)
        draft.reflection = 'Fiquei com dúvida no corte.'
        self.setup.repositories.practice_drafts.find_active.return_value = draft
        self.setup.repositories.practice_photos.list_live_for_draft.return_value = (
            fake_photo(),
            fake_photo(
                photo_id='photo-2',
                record_key='during',
                state=PracticePhotoState.UPLOADING,
            ),
        )

        view = self.subject.execute(*self.setup.scope)

        assert view.revision == 4
        assert view.reflection == 'Fiquei com dúvida no corte.'
        assert [(item.record_key, item.state) for item in view.photos] == [
            ('cuts', PracticePhotoState.READY),
            ('during', PracticePhotoState.UPLOADING),
        ]

    def test_should_deny_a_goal_owned_by_another_account(self) -> None:
        self.setup.repositories.goals.find_by_id.return_value = GoalFaker.fake(
            id='goal-1', account_id='other-account'
        )

        with pytest.raises(NotFoundError):
            self.subject.execute(*self.setup.scope)

    def test_should_deny_an_activity_without_a_practical_question(self) -> None:
        self.setup.curriculum.get_learning_activity.return_value = None

        with pytest.raises(NotFoundError):
            self.subject.execute(*self.setup.scope)

    def test_should_deny_a_competency_whose_content_is_not_released(self) -> None:
        progress = self.setup.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value
        progress.content_released = False

        with pytest.raises(NotFoundError):
            self.subject.execute(*self.setup.scope)

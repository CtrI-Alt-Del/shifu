from shifu.learning.core.domain.enums import PracticeDraftStatus, PracticePhotoState
from shifu.learning.core.use_cases import DiscardPracticeDraftUseCase
from tests.learning.core.use_cases.practice_draft_use_case_setup import (
    PracticeDraftUseCaseSetup,
    fake_draft,
    fake_photo,
)


class TestDiscardPracticeDraftUseCase:
    def setup_method(self) -> None:
        self.setup = PracticeDraftUseCaseSetup()
        self.repositories = self.setup.repositories
        self.subject = DiscardPracticeDraftUseCase(
            self.setup.database, self.setup.curriculum, self.setup.clock
        )

    def test_should_remove_every_photo_request_cleanup_and_close_the_draft(
        self,
    ) -> None:
        draft = fake_draft(revision=3)
        photos = (
            fake_photo(),
            fake_photo(photo_id='photo-2', record_key='during'),
            fake_photo(photo_id='photo-3', record_key='final'),
        )
        self.repositories.practice_drafts.find_active_for_update.return_value = draft
        self.repositories.practice_photos.list_live_for_draft.return_value = photos

        self.subject.execute(*self.setup.scope)

        assert all(item.state is PracticePhotoState.REMOVED for item in photos)
        requested = [
            call.args[0].payload.photo_id
            for call in self.repositories.events.add.call_args_list
        ]
        assert requested == ['photo-1', 'photo-2', 'photo-3']
        assert draft.status is PracticeDraftStatus.CONSUMED
        self.repositories.practice_drafts.update.assert_called_once_with(draft)

    def test_should_do_nothing_without_a_draft(self) -> None:
        self.subject.execute(*self.setup.scope)

        self.repositories.events.add.assert_not_called()
        self.repositories.practice_drafts.update.assert_not_called()

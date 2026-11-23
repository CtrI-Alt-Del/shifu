import pytest

from shifu.learning.core.domain.enums import PracticePhotoOwnerKind, PracticePhotoState
from shifu.learning.core.use_cases import GetPracticePhotoUseCase
from shifu.shared.core.domain.errors import NotFoundError
from tests.fixtures.practice_photo_storage_fixture import PracticePhotoStorageStub
from tests.learning.core.use_cases.practice_draft_use_case_setup import (
    PracticeDraftUseCaseSetup,
    fake_draft,
    fake_photo,
)


class TestGetPracticePhotoUseCase:
    def setup_method(self) -> None:
        self.setup = PracticeDraftUseCaseSetup()
        self.repositories = self.setup.repositories
        self.storage = PracticePhotoStorageStub()
        self.subject = GetPracticePhotoUseCase(
            self.setup.database, self.setup.curriculum, self.storage
        )
        self.repositories.practice_drafts.find_active.return_value = fake_draft()

    def test_should_return_the_bytes_and_media_type_of_a_ready_photo(self) -> None:
        photo = fake_photo()
        self.storage.objects[photo.object_key] = b'bytes'
        self.repositories.practice_photos.find_live_for_record.return_value = photo

        content = self.subject.execute(*self.setup.scope, 'cuts')

        assert (content.media_type, content.content) == ('image/jpeg', b'bytes')

    @pytest.mark.parametrize(
        'state', [PracticePhotoState.UPLOADING, PracticePhotoState.FAILED]
    )
    def test_should_hide_a_photo_that_is_not_ready(
        self, state: PracticePhotoState
    ) -> None:
        self.repositories.practice_photos.find_live_for_record.return_value = (
            fake_photo(state=state)
        )

        with pytest.raises(NotFoundError):
            self.subject.execute(*self.setup.scope, 'cuts')

    def test_should_hide_a_photo_owned_by_an_attempt(self) -> None:
        photo = fake_photo()
        photo.owner_kind = PracticePhotoOwnerKind.ATTEMPT
        self.repositories.practice_photos.find_live_for_record.return_value = photo

        with pytest.raises(NotFoundError):
            self.subject.execute(*self.setup.scope, 'cuts')

    def test_should_hide_a_missing_photo_and_an_unknown_record(self) -> None:
        with pytest.raises(NotFoundError):
            self.subject.execute(*self.setup.scope, 'cuts')

        with pytest.raises(NotFoundError):
            self.subject.execute(*self.setup.scope, 'unknown')

from datetime import UTC, datetime

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.enums import PracticePhotoOwnerKind, PracticePhotoState
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.learning.core.use_cases import PurgePracticePhotosUseCase
from shifu.shared.core.domain.errors import ServiceUnavailableError
from tests.fixtures.practice_photo_storage_fixture import PracticePhotoStorageStub
from tests.learning.core.use_cases.practice_draft_use_case_setup import (
    PracticeDraftUseCaseSetup,
    fake_draft,
    fake_photo,
)

OBJECT_KEY = 'practice-photos/photo-1/original'


class TestPurgePracticePhotosUseCase:
    def setup_method(self) -> None:
        self.setup = PracticeDraftUseCaseSetup()
        self.repositories = self.setup.repositories
        self.storage = PracticePhotoStorageStub()
        self.storage.objects[OBJECT_KEY] = b'bytes'
        self.subject = PurgePracticePhotosUseCase(self.setup.database, self.storage)

    def _removed_photo(self) -> None:
        photo = fake_photo(state=PracticePhotoState.REMOVED)
        photo.removal_due_at = datetime(2026, 11, 22, tzinfo=UTC)
        self.repositories.practice_photos.find_by_id.return_value = photo

    def test_should_delete_the_object_and_clear_the_mark_of_a_removed_photo(
        self,
    ) -> None:
        self._removed_photo()

        deleted = self.subject.execute('photo-1', OBJECT_KEY)

        assert deleted is True
        assert self.storage.objects == {}
        self.repositories.practice_photos.remove.assert_called_once_with('photo-1')

    def test_should_delete_an_orphan_object_when_the_row_is_already_gone(self) -> None:
        self.repositories.practice_photos.find_by_id.return_value = None

        assert self.subject.execute('photo-1', OBJECT_KEY) is True

        assert self.storage.objects == {}
        self.repositories.practice_photos.remove.assert_not_called()

    def test_should_never_delete_an_object_owned_by_an_attempt(self) -> None:
        photo = fake_photo(state=PracticePhotoState.READY)
        photo.owner_kind = PracticePhotoOwnerKind.ATTEMPT
        self.repositories.practice_photos.find_by_id.return_value = photo

        assert self.subject.execute('photo-1', OBJECT_KEY) is False

        assert OBJECT_KEY in self.storage.objects
        self.repositories.practice_photos.remove.assert_not_called()

    def test_should_never_delete_the_object_of_a_live_draft_photo(self) -> None:
        self.repositories.practice_photos.find_by_id.return_value = fake_photo()

        assert self.subject.execute('photo-1', OBJECT_KEY) is False

        assert OBJECT_KEY in self.storage.objects

    def test_should_keep_the_mark_and_raise_for_retry_when_storage_fails(self) -> None:
        self._removed_photo()
        self.storage.fail_remove = True

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('photo-1', OBJECT_KEY)

        self.repositories.practice_photos.remove.assert_not_called()

    def test_should_delete_a_failed_upload_object_and_keep_its_row(self) -> None:
        self.repositories.practice_photos.find_by_id.return_value = fake_photo(
            state=PracticePhotoState.FAILED
        )

        assert self.subject.execute('photo-1', OBJECT_KEY) is True

        self.repositories.practice_photos.remove.assert_not_called()

    @pytest.mark.parametrize(
        ('photo_id', 'object_key'),
        [
            ('photo-1', 'practice-photos/other/original'),
            ('', 'practice-photos//original'),
            ('photo-1', '../etc/passwd'),
        ],
    )
    def test_should_refuse_an_object_key_outside_the_policy(
        self, photo_id: str, object_key: str
    ) -> None:
        with pytest.raises(InvalidAttemptError):
            self.subject.execute(photo_id, object_key)

        assert OBJECT_KEY in self.storage.objects

    def test_should_purge_every_draft_photo_and_object_of_a_closed_account(
        self,
    ) -> None:
        experience = SkillExperienceFaker.fake(id='experience-1')
        self.repositories.goals.find_many_by_account_id.return_value = [
            GoalFaker.fake(id='goal-1', account_id='account-1')
        ]
        self.repositories.skill_experiences.find_many_by_goal_id.return_value = [
            experience
        ]
        self.repositories.practice_drafts.find_many_by_skill_experience_id.return_value = [
            fake_draft()
        ]
        self.repositories.practice_photos.list_for_skill_experience.return_value = (
            fake_photo(),
        )

        removed = self.subject.execute_for_deleted_account('account-1')

        assert removed == 1
        assert self.storage.objects == {}
        self.repositories.practice_photos.remove.assert_called_once_with('photo-1')
        self.repositories.practice_drafts.remove.assert_called_once_with('draft-1')

    def test_should_refuse_a_blank_account_id(self) -> None:
        with pytest.raises(InvalidAttemptError):
            self.subject.execute_for_deleted_account('  ')

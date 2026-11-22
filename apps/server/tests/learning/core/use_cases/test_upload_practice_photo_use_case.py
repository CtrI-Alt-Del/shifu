# pyright: reportUnknownLambdaType=false
from typing import TYPE_CHECKING
from unittest.mock import create_autospec

import hashlib

import pytest

from shifu.fakers.learning.entities import ActivityEvaluationFaker, GoalFaker
from shifu.learning.core.domain.enums import (
    PracticeDraftStatus,
    PracticePhotoState,
)
from shifu.learning.core.domain.errors import (
    PracticePhotoInvalidError,
    PracticePhotoTooLargeError,
)
from shifu.learning.core.domain.events import PracticePhotoCleanupRequestedEvent
from shifu.learning.core.domain.structures import (
    PracticeDraftView,
    PracticePhotoUpload,
)
from shifu.learning.core.interfaces import PracticePhotoInspectorProvider
from shifu.learning.core.use_cases import UploadPracticePhotoUseCase
from shifu.shared.core.domain.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from shifu.shared.core.interfaces import FileStorageProvider
from tests.fixtures.practice_photo_storage_fixture import (
    PracticePhotoImages,
    PracticePhotoStorageStub,
)
from tests.learning.core.use_cases.practice_draft_use_case_setup import (
    PracticeDraftUseCaseSetup,
    fake_draft,
    fake_photo,
)

if TYPE_CHECKING:
    from shifu.learning.core.domain.entities import PracticeDraft, PracticePhoto

UPLOAD_KEY = '8b3a3f4e-2f1c-4c52-9d0b-1c2d3e4f5a6b'
JPEG = PracticePhotoImages.build('image/jpeg')


def _upload(
    content: bytes = JPEG,
    *,
    filename: str = 'prato.jpg',
    media_type: str = 'image/jpeg',
) -> PracticePhotoUpload:
    return PracticePhotoUpload(
        filename=filename, media_type=media_type, content=content
    )


class TestUploadPracticePhotoUseCase:
    def setup_method(self) -> None:
        self.setup = PracticeDraftUseCaseSetup()
        self.setup.identifiers.generate.side_effect = ['draft-new', 'photo-new']
        self.repositories = self.setup.repositories
        self.storage = PracticePhotoStorageStub()
        self.inspector = create_autospec(PracticePhotoInspectorProvider, instance=True)
        self.inspector.sanitize.side_effect = lambda content, _media_type: content
        self.subject = UploadPracticePhotoUseCase(
            self.setup.database,
            self.setup.curriculum,
            self.setup.identifiers,
            self.setup.clock,
            self.storage,
            self.inspector,
        )
        self.drafts: list[PracticeDraft] = []
        self.photos: list[PracticePhoto] = []
        self.repositories.practice_drafts.add.side_effect = self.drafts.append
        self.repositories.practice_photos.add.side_effect = self.photos.append
        self.repositories.practice_drafts.find_active.side_effect = lambda *_: (
            self.drafts[0] if self.drafts else None
        )
        self.repositories.practice_drafts.find_active_for_update.side_effect = (
            lambda *_: self.drafts[0] if self.drafts else None
        )
        self.repositories.practice_photos.find_by_id.side_effect = lambda photo_id: (
            next((item for item in self.photos if item.id == photo_id), None)
        )
        self.repositories.practice_photos.list_live_for_draft.side_effect = (
            lambda _draft_id: tuple(item for item in self.photos if item.is_live)
        )

    def _execute(
        self,
        uploaded: PracticePhotoUpload | None = None,
        *,
        record_key: str = 'cuts',
        upload_key: str = UPLOAD_KEY,
    ) -> PracticeDraftView:
        return self.subject.execute(
            *self.setup.scope, record_key, upload_key, uploaded or _upload()
        )

    def test_should_store_the_object_and_return_a_ready_photo_with_a_new_revision(
        self,
    ) -> None:
        view = self._execute()

        assert view.revision == 1
        assert [(item.record_key, item.state) for item in view.photos] == [
            ('cuts', PracticePhotoState.READY)
        ]
        assert list(self.storage.objects) == ['practice-photos/photo-new/original']
        assert self.photos[0].sha256
        self.inspector.sanitize.assert_called_once_with(JPEG, 'image/jpeg')

    @pytest.mark.parametrize('media_type', ['image/png', 'image/webp'])
    def test_should_accept_png_and_webp(self, media_type: str) -> None:
        name, content, declared = PracticePhotoImages.file(media_type)

        view = self._execute(
            _upload(content, filename=name, media_type=declared),
        )

        assert view.photos[0].media_type == media_type

    def test_should_accept_a_photo_of_exactly_ten_megabytes(self) -> None:
        content = JPEG + b'\0' * (10 * 1024 * 1024 - len(JPEG))

        view = self._execute(_upload(content))

        assert view.photos[0].size_bytes == 10 * 1024 * 1024

    def test_should_reject_one_byte_over_ten_megabytes_without_writing(self) -> None:
        content = JPEG + b'\0' * (10 * 1024 * 1024 + 1 - len(JPEG))

        with pytest.raises(PracticePhotoTooLargeError):
            self._execute(_upload(content))

        assert self.storage.objects == {}
        self.repositories.practice_photos.add.assert_not_called()

    @pytest.mark.parametrize(
        'uploaded',
        [
            _upload(b''),
            _upload(b'plain text', filename='nota.jpg'),
            _upload(JPEG, filename='prato.png'),
            _upload(JPEG, filename='prato.jpg', media_type='image/png'),
            _upload(JPEG, filename='prato'),
            _upload(JPEG, filename='prato.gif', media_type='image/gif'),
            _upload(
                PracticePhotoImages.build('image/png'),
                filename='prato.jpg',
                media_type='image/jpeg',
            ),
        ],
        ids=[
            'empty',
            'not-an-image',
            'extension-mismatch',
            'declared-mismatch',
            'no-extension',
            'unsupported-type',
            'magic-bytes-mismatch',
        ],
    )
    def test_should_reject_invalid_files_without_writing(
        self, uploaded: PracticePhotoUpload
    ) -> None:
        with pytest.raises(PracticePhotoInvalidError):
            self._execute(uploaded)

        assert self.storage.objects == {}
        self.repositories.practice_photos.add.assert_not_called()

    def test_should_reject_an_undecodable_image_reported_by_the_inspector(self) -> None:
        self.inspector.sanitize.side_effect = PracticePhotoInvalidError

        with pytest.raises(PracticePhotoInvalidError):
            self._execute()

        self.repositories.practice_photos.add.assert_not_called()

    @pytest.mark.parametrize(
        'upload_key', ['not-a-uuid', '00000000-0000-1000-8000-000000000000']
    )
    def test_should_reject_an_upload_key_that_is_not_a_uuid4(
        self, upload_key: str
    ) -> None:
        with pytest.raises(PracticePhotoInvalidError):
            self._execute(upload_key=upload_key)

    def test_should_reject_a_record_the_activity_does_not_request(self) -> None:
        with pytest.raises(ValidationError):
            self._execute(record_key='unknown')

        self.repositories.practice_photos.add.assert_not_called()

    def test_should_not_duplicate_the_photo_when_the_upload_key_repeats(self) -> None:
        self._execute()
        self.setup.identifiers.generate.side_effect = ['unused-1', 'unused-2']
        self.repositories.practice_photos.find_by_upload_key.side_effect = lambda *_: (
            self.photos[0]
        )
        self.storage.objects.clear()

        view = self._execute()

        assert len(self.photos) == 1
        assert [item.photo_id for item in view.photos] == ['photo-new']
        assert self.storage.objects == {}

    def test_should_refuse_a_repeated_upload_key_with_different_content(self) -> None:
        self._execute()
        self.repositories.practice_photos.find_by_upload_key.side_effect = lambda *_: (
            self.photos[0]
        )

        with pytest.raises(ConflictError):
            self._execute(_upload(PracticePhotoImages.build('image/jpeg', size=(9, 9))))

    def test_should_remove_the_previous_photo_and_request_its_cleanup_on_replace(
        self,
    ) -> None:
        self.setup.identifiers.generate.side_effect = ['photo-new']
        draft = fake_draft(revision=2)
        self.drafts.append(draft)
        previous = fake_photo(photo_id='old-photo')
        previous.draft_id = draft.id
        self.photos.append(previous)
        self.repositories.practice_photos.find_live_for_record.return_value = previous

        view = self._execute()

        assert previous.state is PracticePhotoState.REMOVED
        assert previous.removal_due_at is not None
        event = self.repositories.events.add.call_args.args[0]
        assert isinstance(event, PracticePhotoCleanupRequestedEvent)
        assert event.payload.photo_id == 'old-photo'
        assert event.payload.object_key == 'practice-photos/old-photo/original'
        assert view.revision == 4
        assert [item.photo_id for item in view.photos] == ['photo-new']

    def test_should_mark_the_photo_failed_and_request_cleanup_when_storage_fails(
        self,
    ) -> None:
        self.storage.fail_put = True

        view = self._execute()

        assert [item.state for item in view.photos] == [PracticePhotoState.FAILED]
        event = self.repositories.events.add.call_args.args[0]
        assert event.payload.photo_id == 'photo-new'
        assert self.storage.objects == {}

    def test_should_refuse_the_upload_while_an_evaluation_is_unresolved(self) -> None:
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = ActivityEvaluationFaker.fake()

        with pytest.raises(ConflictError):
            self._execute()

        self.repositories.practice_photos.add.assert_not_called()

    def test_should_discard_a_late_object_when_the_draft_was_closed_meanwhile(
        self,
    ) -> None:
        original_put = self.storage.put

        def put_then_close(object_key: str, content: bytes, media_type: str) -> None:
            original_put(object_key, content, media_type)
            self.drafts[0].status = PracticeDraftStatus.CONSUMED

        storage = create_autospec(FileStorageProvider, instance=True)
        storage.put.side_effect = put_then_close
        storage.remove.side_effect = self.storage.remove
        self.subject = UploadPracticePhotoUseCase(
            self.setup.database,
            self.setup.curriculum,
            self.setup.identifiers,
            self.setup.clock,
            storage,
            self.inspector,
        )
        self.repositories.practice_drafts.find_active_for_update.side_effect = (
            lambda *_: (
                self.drafts[0]
                if self.drafts and self.drafts[0].status is PracticeDraftStatus.ACTIVE
                else None
            )
        )

        with pytest.raises(ConflictError):
            self._execute()

        assert self.storage.objects == {}
        event = self.repositories.events.add.call_args.args[0]
        assert event.payload.photo_id == 'photo-new'

    def test_should_discard_a_late_object_when_the_experience_disappeared(self) -> None:
        storage = create_autospec(FileStorageProvider, instance=True)
        storage.put.side_effect = lambda *_: setattr(
            self.repositories.skill_experiences.find_by_id_for_update,
            'return_value',
            None,
        )
        self.subject = UploadPracticePhotoUseCase(
            self.setup.database,
            self.setup.curriculum,
            self.setup.identifiers,
            self.setup.clock,
            storage,
            self.inspector,
        )

        with pytest.raises(NotFoundError):
            self._execute()

        storage.remove.assert_called_once_with('practice-photos/photo-new/original')
        event = self.repositories.events.add.call_args.args[0]
        assert event.payload.object_key == 'practice-photos/photo-new/original'

    def test_should_store_and_checksum_the_sanitized_bytes(self) -> None:
        self.inspector.sanitize.side_effect = lambda _content, _media_type: b'clean'

        view = self._execute()

        assert self.storage.objects == {'practice-photos/photo-new/original': b'clean'}
        assert view.photos[0].size_bytes == 5
        assert self.photos[0].sha256 == hashlib.sha256(b'clean').hexdigest()

    def test_should_refuse_sanitized_bytes_over_the_limit(self) -> None:
        self.inspector.sanitize.side_effect = lambda _content, _media_type: bytes(
            10 * 1024 * 1024 + 1
        )

        with pytest.raises(PracticePhotoTooLargeError):
            self._execute()

        self.repositories.practice_photos.add.assert_not_called()

    def test_should_not_decode_for_a_non_owner(self) -> None:
        self.repositories.goals.find_by_id.return_value = GoalFaker.fake(
            id='goal-1', account_id='other-account'
        )

        with pytest.raises(NotFoundError):
            self._execute()

        self.inspector.sanitize.assert_not_called()

    def test_should_not_decode_for_an_unknown_record(self) -> None:
        with pytest.raises(ValidationError):
            self._execute(record_key='unknown')

        self.inspector.sanitize.assert_not_called()

    def test_should_keep_the_object_when_a_concurrent_retry_already_made_it_ready(
        self,
    ) -> None:
        original_put = self.storage.put

        def put_then_complete_elsewhere(
            object_key: str, content: bytes, media_type: str
        ) -> None:
            original_put(object_key, content, media_type)
            self.photos[0].mark_ready()

        storage = create_autospec(FileStorageProvider, instance=True)
        storage.put.side_effect = put_then_complete_elsewhere
        self.subject = UploadPracticePhotoUseCase(
            self.setup.database,
            self.setup.curriculum,
            self.setup.identifiers,
            self.setup.clock,
            storage,
            self.inspector,
        )

        view = self._execute()

        assert [item.state for item in view.photos] == [PracticePhotoState.READY]
        storage.remove.assert_not_called()
        self.repositories.events.add.assert_not_called()

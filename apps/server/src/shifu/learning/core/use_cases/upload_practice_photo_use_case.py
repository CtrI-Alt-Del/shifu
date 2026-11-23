import hashlib
from contextlib import suppress
from uuid import UUID

from shifu.learning.core.domain.entities import PracticeDraft, PracticePhoto
from shifu.learning.core.domain.enums import PracticePhotoState
from shifu.learning.core.domain.errors import (
    PracticePhotoInvalidError,
    PracticePhotoTooLargeError,
)
from shifu.learning.core.domain.structures import PracticeDraftView, PracticePhotoUpload
from shifu.learning.core.interfaces import (
    LearningDatabase,
    PracticePhotoInspectorProvider,
)
from shifu.learning.core.use_cases.practice_draft_access import PracticeDraftAccess
from shifu.learning.core.use_cases.practice_photo_cleanup import PracticePhotoCleanup
from shifu.learning.core.use_cases.practice_photo_object_key import (
    PracticePhotoObjectKey,
)
from shifu.shared.core.domain.errors import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    FileStorageProvider,
    IdentifierProvider,
)

MAX_PHOTO_BYTES = 10 * 1024 * 1024
_MEDIA_TYPES_BY_EXTENSION = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.webp': 'image/webp',
}


class UploadPracticePhotoUseCase:
    def __init__(
        self,
        learning_database: LearningDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        identifier_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        storage_provider: FileStorageProvider,
        inspector_provider: PracticePhotoInspectorProvider,
    ) -> None:
        self._learning_database = learning_database
        self._access = PracticeDraftAccess(curriculum_content_provider)
        self._identifier_provider = identifier_provider
        self._clock_provider = clock_provider
        self._storage_provider = storage_provider
        self._inspector_provider = inspector_provider

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        record_key: str,
        upload_key: str,
        uploaded: PracticePhotoUpload,
    ) -> PracticeDraftView:
        upload_key = self._validate_upload_key(upload_key)
        media_type = self._validate_file(uploaded)
        self._authorize(account_id, goal_id, skill_id, competency_id)
        record_keys = self._access.record_keys(activity_id, competency_id)
        if record_key not in record_keys:
            raise ValidationError

        content = self._inspector_provider.sanitize(uploaded.content, media_type)
        if len(content) > MAX_PHOTO_BYTES:
            raise PracticePhotoTooLargeError

        checksum = hashlib.sha256(content).hexdigest()
        photo, resume = self._reserve(
            account_id,
            goal_id,
            skill_id,
            competency_id,
            activity_id,
            record_key,
            upload_key,
            media_type,
            len(content),
            checksum,
        )
        if not resume:
            return self._view(account_id, goal_id, skill_id, competency_id, activity_id)

        try:
            self._storage_provider.put(photo.object_key, content, media_type)
        except ServiceUnavailableError:
            self._mark_failed(
                account_id, goal_id, skill_id, competency_id, activity_id, photo.id
            )
            return self._view(account_id, goal_id, skill_id, competency_id, activity_id)

        self._complete(account_id, goal_id, skill_id, competency_id, activity_id, photo)
        return self._view(account_id, goal_id, skill_id, competency_id, activity_id)

    def _authorize(
        self, account_id: str, goal_id: str, skill_id: str, competency_id: str
    ) -> None:
        with self._learning_database.transaction() as repositories:
            PracticeDraftAccess.locate(
                repositories,
                account_id,
                goal_id,
                skill_id,
                competency_id,
                for_update=False,
            )

    def _reserve(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        record_key: str,
        upload_key: str,
        media_type: str,
        size_bytes: int,
        checksum: str,
    ) -> tuple[PracticePhoto, bool]:
        now = self._clock_provider.now()
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
            if draft is None:
                draft = PracticeDraft.create(
                    id=self._identifier_provider.generate(),
                    skill_experience_id=experience.id,
                    activity_id=activity_id,
                )
                repositories.practice_drafts.add(draft)

            existing = repositories.practice_photos.find_by_upload_key(
                draft.id, upload_key
            )
            if existing is not None:
                if existing.record_key != record_key or existing.sha256 != checksum:
                    raise ConflictError
                return existing, existing.state is PracticePhotoState.UPLOADING

            previous = repositories.practice_photos.find_live_for_record(
                draft.id, record_key
            )
            if previous is not None:
                previous.mark_removed(now)
                repositories.practice_photos.update(previous)
                PracticePhotoCleanup.request(
                    repositories, previous.id, previous.object_key
                )
                draft.bump_revision()
                repositories.practice_drafts.update(draft)

            photo_id = self._identifier_provider.generate()
            photo = PracticePhoto.create(
                id=photo_id,
                draft_id=draft.id,
                record_key=record_key,
                object_key=PracticePhotoObjectKey.for_photo(photo_id),
                media_type=media_type,
                size_bytes=size_bytes,
                sha256=checksum,
                upload_key=upload_key,
            )
            repositories.practice_photos.add(photo)
            return photo, True

    def _mark_failed(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        photo_id: str,
    ) -> None:
        with self._learning_database.transaction() as repositories:
            experience = PracticeDraftAccess.locate(
                repositories,
                account_id,
                goal_id,
                skill_id,
                competency_id,
                for_update=True,
            )
            photo = repositories.practice_photos.find_by_id(photo_id)
            if photo is None:
                return

            if photo.state is PracticePhotoState.UPLOADING:
                photo.mark_failed()
                repositories.practice_photos.update(photo)
                draft = repositories.practice_drafts.find_active_for_update(
                    experience.id, activity_id
                )
                if draft is not None and draft.id == photo.draft_id:
                    draft.bump_revision()
                    repositories.practice_drafts.update(draft)

            if photo.state is not PracticePhotoState.READY:
                PracticePhotoCleanup.request(repositories, photo.id, photo.object_key)

    def _complete(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        photo: PracticePhoto,
    ) -> None:
        try:
            completed = self._mark_ready(
                account_id, goal_id, skill_id, competency_id, activity_id, photo.id
            )
        except NotFoundError:
            self._discard_late_object(photo)
            raise

        if not completed:
            self._discard_late_object(photo)
            raise ConflictError

    def _mark_ready(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
        photo_id: str,
    ) -> bool:
        with self._learning_database.transaction() as repositories:
            experience = PracticeDraftAccess.locate(
                repositories,
                account_id,
                goal_id,
                skill_id,
                competency_id,
                for_update=True,
            )
            draft = repositories.practice_drafts.find_active_for_update(
                experience.id, activity_id
            )
            current = repositories.practice_photos.find_by_id(photo_id)
            if current is None or draft is None or current.draft_id != draft.id:
                return False

            if current.state is PracticePhotoState.READY:
                # A concurrent retry with the same upload key already completed it.
                return True

            if current.state is not PracticePhotoState.UPLOADING:
                return False

            current.mark_ready()
            repositories.practice_photos.update(current)
            draft.bump_revision()
            repositories.practice_drafts.update(draft)
            return True

    def _discard_late_object(self, photo: PracticePhoto) -> None:
        """Remove bytes written after the draft, photo or experience went away."""
        with suppress(ServiceUnavailableError):
            self._storage_provider.remove(photo.object_key)

        with self._learning_database.transaction() as repositories:
            PracticePhotoCleanup.request(repositories, photo.id, photo.object_key)

    def _view(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        activity_id: str,
    ) -> PracticeDraftView:
        with self._learning_database.transaction() as repositories:
            experience = PracticeDraftAccess.locate(
                repositories,
                account_id,
                goal_id,
                skill_id,
                competency_id,
                for_update=False,
            )
            draft = repositories.practice_drafts.find_active(experience.id, activity_id)
            photos = (
                repositories.practice_photos.list_live_for_draft(draft.id)
                if draft is not None
                else ()
            )
            return PracticeDraftAccess.view(draft, photos)

    @staticmethod
    def _validate_file(uploaded: PracticePhotoUpload) -> str:
        content = uploaded.content
        if type(content) is not bytes or not content:
            raise PracticePhotoInvalidError
        if len(content) > MAX_PHOTO_BYTES:
            raise PracticePhotoTooLargeError

        filename = uploaded.filename.strip().replace('\\', '/').rsplit('/', 1)[-1]
        extension = (
            '.' + filename.rsplit('.', 1)[-1].casefold() if '.' in filename else ''
        )
        media_type = _MEDIA_TYPES_BY_EXTENSION.get(extension)
        declared = uploaded.media_type.split(';', maxsplit=1)[0].strip().lower()
        if (
            media_type is None
            or declared != media_type
            or UploadPracticePhotoUseCase._sniff(content) != media_type
        ):
            raise PracticePhotoInvalidError

        return media_type

    @staticmethod
    def _sniff(content: bytes) -> str | None:
        if content.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        if content.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        if content[:4] == b'RIFF' and content[8:12] == b'WEBP':
            return 'image/webp'
        return None

    @staticmethod
    def _validate_upload_key(upload_key: str) -> str:
        try:
            parsed = UUID(upload_key)
        except (ValueError, AttributeError) as error:
            raise PracticePhotoInvalidError from error
        if parsed.version != 4 or str(parsed) != upload_key.lower():
            raise PracticePhotoInvalidError
        return str(parsed)

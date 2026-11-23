from datetime import datetime, timedelta

from shifu.learning.core.domain.enums import (
    PracticePhotoOwnerKind,
    PracticePhotoState,
)
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.entities import entity

REMOVAL_RETENTION = timedelta(hours=24)


@entity
class PracticePhoto:
    id: str
    owner_kind: PracticePhotoOwnerKind
    draft_id: str | None
    attempt_id: str | None
    record_key: str
    object_key: str
    media_type: str
    size_bytes: int
    sha256: str
    state: PracticePhotoState
    upload_key: str
    removal_due_at: datetime | None

    @classmethod
    def create(
        cls,
        *,
        id: str,
        draft_id: str,
        record_key: str,
        object_key: str,
        media_type: str,
        size_bytes: int,
        sha256: str,
        upload_key: str,
    ) -> 'PracticePhoto':
        if (
            not id
            or not draft_id
            or not record_key
            or not object_key
            or not media_type
            or size_bytes < 1
            or not sha256
            or not upload_key
        ):
            raise InvalidAttemptError

        return cls(
            id=id,
            owner_kind=PracticePhotoOwnerKind.DRAFT,
            draft_id=draft_id,
            attempt_id=None,
            record_key=record_key,
            object_key=object_key,
            media_type=media_type,
            size_bytes=size_bytes,
            sha256=sha256,
            state=PracticePhotoState.UPLOADING,
            upload_key=upload_key,
            removal_due_at=None,
        )

    @property
    def is_live(self) -> bool:
        return self.state is not PracticePhotoState.REMOVED

    def mark_ready(self) -> None:
        if self.state is not PracticePhotoState.UPLOADING:
            raise InvalidAttemptError
        self.state = PracticePhotoState.READY

    def mark_failed(self) -> None:
        if self.state is not PracticePhotoState.UPLOADING:
            raise InvalidAttemptError
        self.state = PracticePhotoState.FAILED

    def mark_removed(self, now: datetime) -> None:
        if self.owner_kind is not PracticePhotoOwnerKind.DRAFT:
            raise InvalidAttemptError
        if self.state is PracticePhotoState.REMOVED:
            return
        self.state = PracticePhotoState.REMOVED
        self.removal_due_at = now + REMOVAL_RETENTION

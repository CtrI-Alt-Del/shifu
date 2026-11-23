from shifu.learning.core.domain.entities.practice_photo import PracticePhoto
from shifu.learning.core.domain.enums import (
    PracticePhotoOwnerKind,
    PracticePhotoState,
)
from shifu.learning.database.sqlalchemy.models import PracticePhotoModel


class PracticePhotoMapper:
    @staticmethod
    def to_domain(model: PracticePhotoModel) -> PracticePhoto:
        return PracticePhoto(
            id=model.id,
            owner_kind=PracticePhotoOwnerKind(model.owner_kind),
            draft_id=model.draft_id,
            attempt_id=model.attempt_id,
            record_key=model.record_key,
            object_key=model.object_key,
            media_type=model.media_type,
            size_bytes=model.size_bytes,
            sha256=model.sha256,
            state=PracticePhotoState(model.state),
            upload_key=model.upload_key,
            removal_due_at=model.removal_due_at,
        )

    @staticmethod
    def to_model(photo: PracticePhoto) -> PracticePhotoModel:
        return PracticePhotoModel(
            id=photo.id,
            owner_kind=photo.owner_kind.value,
            draft_id=photo.draft_id,
            attempt_id=photo.attempt_id,
            record_key=photo.record_key,
            object_key=photo.object_key,
            media_type=photo.media_type,
            size_bytes=photo.size_bytes,
            sha256=photo.sha256,
            state=photo.state.value,
            upload_key=photo.upload_key,
            removal_due_at=photo.removal_due_at,
        )

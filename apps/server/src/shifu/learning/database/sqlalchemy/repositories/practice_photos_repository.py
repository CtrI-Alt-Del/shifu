from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from shifu.learning.core.domain.entities.practice_photo import PracticePhoto
from shifu.learning.database.sqlalchemy.mappers import PracticePhotoMapper
from shifu.learning.database.sqlalchemy.models import (
    ActivityAttemptModel,
    PracticeDraftModel,
    PracticePhotoModel,
)


class SqlalchemyPracticePhotosRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_id(self, photo_id: str) -> PracticePhoto | None:
        model = self._session.get(PracticePhotoModel, photo_id)
        return PracticePhotoMapper.to_domain(model) if model is not None else None

    def list_live_for_draft(self, draft_id: str) -> tuple[PracticePhoto, ...]:
        models = self._session.scalars(
            select(PracticePhotoModel)
            .where(
                PracticePhotoModel.draft_id == draft_id,
                PracticePhotoModel.state != 'removed',
            )
            .order_by(PracticePhotoModel.id)
        )
        return tuple(PracticePhotoMapper.to_domain(model) for model in models)

    def list_ready_for_draft(self, draft_id: str) -> tuple[PracticePhoto, ...]:
        models = self._session.scalars(
            select(PracticePhotoModel)
            .where(
                PracticePhotoModel.draft_id == draft_id,
                PracticePhotoModel.state == 'ready',
            )
            .order_by(PracticePhotoModel.id)
        )
        return tuple(PracticePhotoMapper.to_domain(model) for model in models)

    def list_for_attempt(self, attempt_id: str) -> tuple[PracticePhoto, ...]:
        models = self._session.scalars(
            select(PracticePhotoModel)
            .where(PracticePhotoModel.attempt_id == attempt_id)
            .order_by(PracticePhotoModel.id)
        )
        return tuple(PracticePhotoMapper.to_domain(model) for model in models)

    def find_live_for_record(
        self, draft_id: str, record_key: str
    ) -> PracticePhoto | None:
        model = self._session.scalar(
            select(PracticePhotoModel).where(
                PracticePhotoModel.draft_id == draft_id,
                PracticePhotoModel.record_key == record_key,
                PracticePhotoModel.state != 'removed',
            )
        )
        return PracticePhotoMapper.to_domain(model) if model is not None else None

    def find_by_upload_key(
        self, draft_id: str, upload_key: str
    ) -> PracticePhoto | None:
        model = self._session.scalar(
            select(PracticePhotoModel).where(
                PracticePhotoModel.draft_id == draft_id,
                PracticePhotoModel.upload_key == upload_key,
            )
        )
        return PracticePhotoMapper.to_domain(model) if model is not None else None

    def list_for_skill_experience(
        self, skill_experience_id: str
    ) -> tuple[PracticePhoto, ...]:
        draft_ids = select(PracticeDraftModel.id).where(
            PracticeDraftModel.skill_experience_id == skill_experience_id
        )
        attempt_ids = select(ActivityAttemptModel.id).where(
            ActivityAttemptModel.skill_experience_id == skill_experience_id
        )
        models = self._session.scalars(
            select(PracticePhotoModel)
            .where(
                or_(
                    PracticePhotoModel.draft_id.in_(draft_ids),
                    PracticePhotoModel.attempt_id.in_(attempt_ids),
                )
            )
            .order_by(PracticePhotoModel.id)
        )
        return tuple(PracticePhotoMapper.to_domain(model) for model in models)

    def add(self, photo: PracticePhoto) -> None:
        self._session.add(PracticePhotoMapper.to_model(photo))

    def update(self, photo: PracticePhoto) -> None:
        model = self._session.get(PracticePhotoModel, photo.id)
        if model is None:
            raise ValueError('Practice photo does not exist.')

        mapped = PracticePhotoMapper.to_model(photo)
        model.owner_kind = mapped.owner_kind
        model.draft_id = mapped.draft_id
        model.attempt_id = mapped.attempt_id
        model.state = mapped.state
        model.removal_due_at = mapped.removal_due_at

    def remove(self, photo_id: str) -> None:
        self._session.execute(
            delete(PracticePhotoModel).where(PracticePhotoModel.id == photo_id)
        )

    def reassign_to_attempt(self, draft_id: str, attempt_id: str) -> None:
        self._session.execute(
            update(PracticePhotoModel)
            .where(
                PracticePhotoModel.draft_id == draft_id,
                PracticePhotoModel.state == 'ready',
            )
            .values(owner_kind='attempt', draft_id=None, attempt_id=attempt_id)
        )

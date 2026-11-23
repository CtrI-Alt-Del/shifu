from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.learning.core.domain.entities.practice_draft import PracticeDraft
from shifu.learning.database.sqlalchemy.mappers import PracticeDraftMapper
from shifu.learning.database.sqlalchemy.models import PracticeDraftModel


class SqlalchemyPracticeDraftsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_active(
        self, skill_experience_id: str, activity_id: str
    ) -> PracticeDraft | None:
        model = self._session.scalar(
            select(PracticeDraftModel).where(
                PracticeDraftModel.skill_experience_id == skill_experience_id,
                PracticeDraftModel.activity_id == activity_id,
                PracticeDraftModel.status == 'active',
            )
        )
        return PracticeDraftMapper.to_domain(model) if model is not None else None

    def find_active_for_update(
        self, skill_experience_id: str, activity_id: str
    ) -> PracticeDraft | None:
        model = self._session.scalar(
            select(PracticeDraftModel)
            .where(
                PracticeDraftModel.skill_experience_id == skill_experience_id,
                PracticeDraftModel.activity_id == activity_id,
                PracticeDraftModel.status == 'active',
            )
            .with_for_update()
        )
        return PracticeDraftMapper.to_domain(model) if model is not None else None

    def find_many_by_skill_experience_id(
        self, skill_experience_id: str
    ) -> list[PracticeDraft]:
        models = self._session.scalars(
            select(PracticeDraftModel).where(
                PracticeDraftModel.skill_experience_id == skill_experience_id
            )
        )
        return [PracticeDraftMapper.to_domain(model) for model in models]

    def add(self, draft: PracticeDraft) -> None:
        self._session.add(PracticeDraftMapper.to_model(draft))

    def update(self, draft: PracticeDraft) -> None:
        model = self._session.get(PracticeDraftModel, draft.id)
        if model is None:
            raise ValueError('Practice draft does not exist.')

        mapped = PracticeDraftMapper.to_model(draft)
        model.reflection = mapped.reflection
        model.revision = mapped.revision
        model.status = mapped.status

    def remove(self, draft_id: str) -> None:
        self._session.execute(
            delete(PracticeDraftModel).where(PracticeDraftModel.id == draft_id)
        )

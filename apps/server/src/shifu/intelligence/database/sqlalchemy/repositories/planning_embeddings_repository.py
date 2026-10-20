import math

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from shifu.intelligence.core.domain.structures import (
    PlanningEmbeddingMatch,
    PlanningIndexedEmbedding,
)
from shifu.intelligence.database.sqlalchemy.models.planning_embedding_version_model import (
    PlanningEmbeddingVersionModel,
)
from shifu.intelligence.database.sqlalchemy.models.planning_skill_embedding_model import (
    PlanningSkillEmbeddingModel,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError


class SqlalchemyPlanningEmbeddingsRepository:
    def __init__(self, session: Session) -> None:
        self._session: Session = session

    def prepare_version(
        self, version: str, vectors: tuple[PlanningIndexedEmbedding, ...]
    ) -> None:
        if not version or not vectors:
            raise ValueError('Index version and complete corpus required')
        if len({item.skill_id for item in vectors}) != len(vectors):
            raise ValueError('Duplicate Skill in the planning corpus')
        existing = self._session.get(PlanningEmbeddingVersionModel, version)
        if existing is not None and existing.active:
            raise ValueError('Active immutable index cannot be replaced')
        if existing is None:
            self._session.add(
                PlanningEmbeddingVersionModel(version=version, active=False)
            )
            self._session.flush()
        self._session.execute(
            delete(PlanningSkillEmbeddingModel).where(
                PlanningSkillEmbeddingModel.version == version
            )
        )
        self._session.add_all(
            [
                PlanningSkillEmbeddingModel(
                    version=version,
                    skill_id=item.skill_id,
                    vector=list(item.vector),
                )
                for item in vectors
            ]
        )
        self._session.flush()

    def activate_version(self, version: str) -> None:
        existing = self._session.scalar(
            select(PlanningEmbeddingVersionModel)
            .where(PlanningEmbeddingVersionModel.version == version)
            .with_for_update()
        )
        if existing is None:
            raise ServiceUnavailableError
        has_vectors = self._session.scalar(
            select(PlanningSkillEmbeddingModel.skill_id)
            .where(PlanningSkillEmbeddingModel.version == version)
            .limit(1)
        )
        if has_vectors is None:
            raise ServiceUnavailableError
        self._session.execute(
            update(PlanningEmbeddingVersionModel).values(active=False)
        )
        existing.active = True
        self._session.flush()

    def find_active_version(self) -> str | None:
        return self._session.scalar(
            select(PlanningEmbeddingVersionModel.version).where(
                PlanningEmbeddingVersionModel.active.is_(True)
            )
        )

    def find_nearest(
        self,
        version: str,
        query: tuple[float, ...],
        eligible_skill_ids: tuple[str, ...],
        limit: int,
    ) -> tuple[PlanningEmbeddingMatch, ...]:
        self._validate_vector(query)
        existing = self._session.get(PlanningEmbeddingVersionModel, version)
        if existing is None or not existing.active:
            raise ServiceUnavailableError
        if not eligible_skill_ids or limit < 1:
            return ()
        distance = PlanningSkillEmbeddingModel.vector.cosine_distance(list(query))
        rows = self._session.execute(
            select(PlanningSkillEmbeddingModel.skill_id, distance.label('distance'))
            .where(
                PlanningSkillEmbeddingModel.version == version,
                PlanningSkillEmbeddingModel.skill_id.in_(eligible_skill_ids),
            )
            .order_by(distance, PlanningSkillEmbeddingModel.skill_id)
            .limit(limit)
        ).all()
        return tuple(
            PlanningEmbeddingMatch(
                skill_id=row.skill_id, similarity=1.0 - float(row.distance)
            )
            for row in rows
        )

    @staticmethod
    def _validate_vector(vector: tuple[float, ...]) -> None:
        if len(vector) != 384 or not all(math.isfinite(value) for value in vector):
            raise ValueError('Invalid embedding dimensions or values')
        norm = math.sqrt(sum(value * value for value in vector))
        if not math.isclose(norm, 1.0, rel_tol=1e-4, abs_tol=1e-4):
            raise ValueError('Embedding must be normalized')

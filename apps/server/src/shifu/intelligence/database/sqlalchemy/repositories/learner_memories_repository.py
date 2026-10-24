from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from shifu.intelligence.core.domain.entities import LearnerMemory
from shifu.intelligence.core.domain.structures import (
    LearnerMemoryConcept,
    LearnerMemoryDetails,
    LearnerMemoryFilter,
    LearnerMemoryOrigin,
)
from shifu.intelligence.database.sqlalchemy.mappers import (
    LearnerMemoryConceptMapper,
    LearnerMemoryMapper,
    LearnerMemoryOriginMapper,
)
from shifu.intelligence.database.sqlalchemy.models import (
    LearnerMemoryConceptModel,
    LearnerMemoryFenceModel,
    LearnerMemoryModel,
    LearnerMemoryOriginModel,
    MentorSessionModel,
)
from shifu.shared.core.interfaces import IdentifierProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider


class SqlalchemyLearnerMemoriesRepository:
    def __init__(
        self, session: Session, id_provider: IdentifierProvider | None = None
    ) -> None:
        self._session = session
        self._id_provider: IdentifierProvider = (
            id_provider or SystemIdentifierProvider()
        )

    def lock_account(self, account_id: str) -> datetime | None:
        self._session.execute(
            insert(LearnerMemoryFenceModel)
            .values(account_id=account_id, deleted_through=None)
            .on_conflict_do_nothing(index_elements=['account_id'])
        )
        return self._session.scalar(
            select(LearnerMemoryFenceModel.deleted_through)
            .where(LearnerMemoryFenceModel.account_id == account_id)
            .with_for_update()
        )

    def advance_fence(self, account_id: str, at: datetime) -> None:
        statement = insert(LearnerMemoryFenceModel).values(
            account_id=account_id, deleted_through=at
        )
        self._session.execute(
            statement.on_conflict_do_update(
                index_elements=['account_id'],
                set_={
                    'deleted_through': func.greatest(
                        func.coalesce(
                            LearnerMemoryFenceModel.deleted_through,
                            statement.excluded.deleted_through,
                        ),
                        statement.excluded.deleted_through,
                    )
                },
            )
        )

    def find_many(
        self, account_id: str, filter: LearnerMemoryFilter
    ) -> tuple[LearnerMemoryDetails, ...]:
        query = select(LearnerMemoryModel).where(
            LearnerMemoryModel.account_id == account_id
        )
        if filter.category is not None:
            query = query.where(LearnerMemoryModel.category == filter.category.value)
        if filter.query:
            normalized = LearnerMemoryMapper.to_search_content(filter.query)
            escaped = (
                normalized.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            )
            query = query.where(
                LearnerMemoryModel.content_search.like(f'%{escaped}%', escape='\\')
            )
        models = list(
            self._session.scalars(
                query.order_by(
                    LearnerMemoryModel.updated_at.desc(), LearnerMemoryModel.id
                )
            )
        )
        return self._hydrate(models)

    def find_details(
        self, account_id: str, memory_id: str
    ) -> LearnerMemoryDetails | None:
        model = self._session.scalar(
            select(LearnerMemoryModel).where(
                LearnerMemoryModel.account_id == account_id,
                LearnerMemoryModel.id == memory_id,
            )
        )
        if model is None:
            return None
        return self._hydrate([model])[0]

    def find_many_by_account(self, account_id: str) -> tuple[LearnerMemory, ...]:
        models = self._session.scalars(
            select(LearnerMemoryModel)
            .where(LearnerMemoryModel.account_id == account_id)
            .order_by(LearnerMemoryModel.updated_at.desc(), LearnerMemoryModel.id)
        )
        return tuple(LearnerMemoryMapper.to_entity(model) for model in models)

    def find_by_id_for_update(
        self, account_id: str, memory_id: str
    ) -> LearnerMemory | None:
        model = self._session.scalar(
            select(LearnerMemoryModel)
            .where(
                LearnerMemoryModel.account_id == account_id,
                LearnerMemoryModel.id == memory_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return LearnerMemoryMapper.to_entity(model) if model is not None else None

    def add(
        self,
        memory: LearnerMemory,
        concepts: tuple[LearnerMemoryConcept, ...],
        origin: LearnerMemoryOrigin,
    ) -> None:
        self._session.add(LearnerMemoryMapper.to_model(memory))
        self._session.flush()
        self._session.add_all(LearnerMemoryConceptMapper.to_models(memory.id, concepts))
        self.add_origin(memory.id, origin)

    def update(
        self, memory: LearnerMemory, concepts: tuple[LearnerMemoryConcept, ...]
    ) -> None:
        model = self._session.get(LearnerMemoryModel, memory.id)
        if model is None or model.account_id != memory.account_id:
            raise ValueError('The learner memory is no longer available')
        LearnerMemoryMapper.apply(model, memory)
        self._session.execute(
            delete(LearnerMemoryConceptModel).where(
                LearnerMemoryConceptModel.memory_id == memory.id
            )
        )
        self._session.add_all(LearnerMemoryConceptMapper.to_models(memory.id, concepts))
        self._session.flush()

    def add_origin(self, memory_id: str, origin: LearnerMemoryOrigin) -> None:
        self._session.add(
            LearnerMemoryOriginMapper.to_model(
                self._id_provider.generate(), memory_id, origin
            )
        )
        self._session.flush()

    def remove(self, account_id: str, memory_id: str) -> bool:
        removed = self._session.scalars(
            delete(LearnerMemoryModel)
            .where(
                LearnerMemoryModel.account_id == account_id,
                LearnerMemoryModel.id == memory_id,
            )
            .returning(LearnerMemoryModel.id)
        ).all()
        return len(removed) > 0

    def remove_by_account_id(self, account_id: str) -> int:
        removed = self._session.scalars(
            delete(LearnerMemoryModel)
            .where(LearnerMemoryModel.account_id == account_id)
            .returning(LearnerMemoryModel.id)
        ).all()
        self._session.execute(
            delete(LearnerMemoryFenceModel).where(
                LearnerMemoryFenceModel.account_id == account_id
            )
        )
        return len(removed)

    def remove_all(self) -> None:
        self._session.execute(delete(LearnerMemoryModel))
        self._session.execute(delete(LearnerMemoryFenceModel))

    def _hydrate(
        self, models: list[LearnerMemoryModel]
    ) -> tuple[LearnerMemoryDetails, ...]:
        if not models:
            return ()
        memory_ids = [model.id for model in models]
        origins: dict[str, list[LearnerMemoryOriginModel]] = {}
        titles: dict[str, str | None] = {}
        for origin, title in self._session.execute(
            select(LearnerMemoryOriginModel, MentorSessionModel.title)
            .join(
                MentorSessionModel,
                MentorSessionModel.id == LearnerMemoryOriginModel.session_id,
            )
            .where(LearnerMemoryOriginModel.memory_id.in_(memory_ids))
            .order_by(
                LearnerMemoryOriginModel.declared_at.desc(),
                LearnerMemoryOriginModel.id,
            )
        ):
            origins.setdefault(origin.memory_id, []).append(origin)
            titles[origin.id] = title
        concepts: dict[str, list[LearnerMemoryConceptModel]] = {}
        for concept in self._session.scalars(
            select(LearnerMemoryConceptModel)
            .where(LearnerMemoryConceptModel.memory_id.in_(memory_ids))
            .order_by(
                LearnerMemoryConceptModel.memory_id,
                LearnerMemoryConceptModel.position,
            )
        ):
            concepts.setdefault(concept.memory_id, []).append(concept)
        return tuple(
            LearnerMemoryDetails(
                memory=LearnerMemoryMapper.to_entity(model),
                origins=tuple(
                    LearnerMemoryOriginMapper.to_view(origin, titles[origin.id])
                    for origin in origins.get(model.id, ())
                ),
                concepts=tuple(
                    LearnerMemoryConceptMapper.to_concept(concept)
                    for concept in concepts.get(model.id, ())
                ),
            )
            for model in models
        )

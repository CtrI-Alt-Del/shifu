"""Compose module-owned Planner ports without importing private repositories."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers import DatabaseCurriculumCatalogProvider
from shifu.intelligence.core.interfaces import PlanningEmbeddingsRepository
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.shared.core.interfaces import CurriculumCatalogProvider
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from sqlalchemy import Engine


def build_planning_index_dependencies() -> tuple[
    PlanningEmbeddingsRepository, CurriculumCatalogProvider, Callable[[], None]
]:
    from shifu.intelligence.database.planning_embeddings_database_repository import (
        PlanningEmbeddingsDatabaseRepository,
    )

    engine: Engine = Session.create_database_engine()
    catalog = DatabaseCurriculumCatalogProvider(
        SqlalchemyCurriculumDatabase(engine=engine)
    )
    database = SqlalchemyIntelligenceDatabase(
        engine=engine, id_provider=SystemIdentifierProvider()
    )
    return PlanningEmbeddingsDatabaseRepository(database), catalog, engine.dispose

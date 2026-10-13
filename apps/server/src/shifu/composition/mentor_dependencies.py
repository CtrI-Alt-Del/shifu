"""Compose module-owned Mentor ports without importing private repositories."""

from collections.abc import Callable

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy import Engine

from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers.curriculum_mentor_catalog_provider import (
    CurriculumMentorCatalogProvider,
)
from shifu.intelligence.core.interfaces import (
    MentorEmbeddingsRepository,
)
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.shared.core.interfaces import MentorCatalogProvider
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider


def build_mentor_index_dependencies() -> tuple[
    MentorEmbeddingsRepository, MentorCatalogProvider, Callable[[], None]
]:
    from shifu.intelligence.database.mentor_embeddings_database_repository import (
        MentorEmbeddingsDatabaseRepository,
    )

    engine: Engine = Session.create_database_engine()
    catalog = CurriculumMentorCatalogProvider(
        SqlalchemyCurriculumDatabase(engine=engine)
    )
    database = SqlalchemyIntelligenceDatabase(
        engine=engine, id_provider=SystemIdentifierProvider()
    )
    return MentorEmbeddingsDatabaseRepository(database), catalog, engine.dispose

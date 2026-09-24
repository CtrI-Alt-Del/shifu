from fastapi import Request

from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.interfaces import (
    CurriculumCatalogProvider,
    CurriculumContentProvider,
)


class LearningPipe:
    @staticmethod
    def get_database(request: Request) -> LearningDatabase:
        return request.app.state.learning_database

    @staticmethod
    def get_curriculum_content_provider(
        request: Request,
    ) -> CurriculumContentProvider:
        return request.app.state.curriculum_content_provider

    @staticmethod
    def get_curriculum_catalog_provider(
        request: Request,
    ) -> CurriculumCatalogProvider:
        return request.app.state.curriculum_catalog_provider

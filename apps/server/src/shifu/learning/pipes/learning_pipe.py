from fastapi import Request

from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
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
    def get_clock_provider(request: Request) -> ClockProvider:
        return request.app.state.clock_provider

    @staticmethod
    def get_identifier_provider(request: Request) -> IdentifierProvider:
        return request.app.state.identifier_provider

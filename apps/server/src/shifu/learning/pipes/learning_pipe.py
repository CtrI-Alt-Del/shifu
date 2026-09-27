from fastapi import Request

from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.interfaces import (
    ClockProvider,
    CodeRubricAssessorProvider,
    CurriculumCatalogProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)


class LearningPipe:
    @staticmethod
    def get_code_rubric_assessor_provider(
        request: Request,
    ) -> CodeRubricAssessorProvider:
        return request.app.state.code_rubric_assessor_provider

    @staticmethod
    def get_max_activity_payload_bytes(request: Request) -> int:
        return request.app.state.max_activity_payload_bytes

    @staticmethod
    def get_max_code_assessment_input_bytes(request: Request) -> int:
        return request.app.state.max_code_assessment_input_bytes

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

    @staticmethod
    def get_curriculum_catalog_provider(
        request: Request,
    ) -> CurriculumCatalogProvider:
        return request.app.state.curriculum_catalog_provider

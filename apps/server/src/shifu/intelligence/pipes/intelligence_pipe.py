from fastapi import Request
from sqlalchemy.engine import Engine

from shifu.intelligence.core.interfaces import (
    GenerateMentorTitleProvider,
    IntelligenceDatabase,
    LearnerMemoryAnalyzerProvider,
    MentorAttachmentExtractorProvider,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
)
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider


class IntelligencePipe:
    @staticmethod
    def create_database(engine: Engine | None = None) -> IntelligenceDatabase:
        from shifu.intelligence.database.sqlalchemy import (
            SqlalchemyIntelligenceDatabase,
        )

        return SqlalchemyIntelligenceDatabase(engine=engine)

    @staticmethod
    def get_mentor_access_provider(request: Request) -> MentorAccessProvider:
        return request.app.state.mentor_access_provider

    @staticmethod
    def get_database(request: Request) -> IntelligenceDatabase:
        return request.app.state.intelligence_database

    @staticmethod
    def get_generate_mentor_title_provider(
        request: Request,
    ) -> GenerateMentorTitleProvider:
        return request.app.state.generate_mentor_title_provider

    @staticmethod
    def get_mentor_attachment_extractor_provider(
        request: Request,
    ) -> MentorAttachmentExtractorProvider:
        return request.app.state.mentor_attachment_extractor_provider

    @staticmethod
    def get_learner_memory_analyzer_provider(
        request: Request,
    ) -> LearnerMemoryAnalyzerProvider:
        return request.app.state.learner_memory_analyzer_provider

    @staticmethod
    def get_identifier_provider() -> IdentifierProvider:
        return SystemIdentifierProvider()

    @staticmethod
    def get_clock_provider() -> ClockProvider:
        return SystemClockProvider()

from fastapi import Request

from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider


class IntelligencePipe:
    @staticmethod
    def get_database(request: Request) -> IntelligenceDatabase:
        return request.app.state.intelligence_database

    @staticmethod
    def get_identifier_provider() -> IdentifierProvider:
        return SystemIdentifierProvider()

    @staticmethod
    def get_clock_provider() -> ClockProvider:
        return SystemClockProvider()

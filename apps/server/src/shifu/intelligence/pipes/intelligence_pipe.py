from fastapi import Request

from shifu.intelligence.core.interfaces import IntelligenceDatabase


class IntelligencePipe:
    @staticmethod
    def get_database(request: Request) -> IntelligenceDatabase:
        return request.app.state.intelligence_database

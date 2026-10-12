from fastapi import Request

from shifu.gamification.core.interfaces import GamificationDatabase


class GamificationPipe:
    @staticmethod
    def get_database(request: Request) -> GamificationDatabase:
        return request.app.state.gamification_database

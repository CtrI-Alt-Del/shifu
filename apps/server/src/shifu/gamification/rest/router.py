from fastapi import APIRouter


class GamificationRouter:
    @staticmethod
    def register() -> APIRouter:
        return APIRouter(prefix="/gamification", tags=["gamification"])


__all__ = ["GamificationRouter"]

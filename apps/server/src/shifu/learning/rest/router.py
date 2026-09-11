from fastapi import APIRouter


class LearningRouter:
    @staticmethod
    def register() -> APIRouter:
        return APIRouter(prefix='/learning', tags=['learning'])

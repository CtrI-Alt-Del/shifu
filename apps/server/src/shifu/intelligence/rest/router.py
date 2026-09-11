from fastapi import APIRouter


class IntelligenceRouter:
    @staticmethod
    def register() -> APIRouter:
        return APIRouter(prefix='/intelligence', tags=['intelligence'])

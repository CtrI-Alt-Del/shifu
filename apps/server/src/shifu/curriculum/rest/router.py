from fastapi import APIRouter


class CurriculumRouter:
    @staticmethod
    def register() -> APIRouter:
        return APIRouter(prefix='/curriculum', tags=['curriculum'])

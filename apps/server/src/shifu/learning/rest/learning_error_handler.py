from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from shifu.learning.core.domain.errors import CurriculumGapError


class LearningErrorHandler:
    @staticmethod
    async def handle_curriculum_gap_error(
        _request: Request, _error: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                'code': 'curriculum_gap',
                'message': 'Um Skill selecionado ainda não está pronto para iniciar.',
            },
        )

    @staticmethod
    def register(app: FastAPI) -> None:
        app.add_exception_handler(
            CurriculumGapError,
            LearningErrorHandler.handle_curriculum_gap_error,
        )

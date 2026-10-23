from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from shifu.intelligence.core.domain.errors import (
    LearnerMemoryContentInvalidError,
    MentorCursorInvalidError,
)


class IntelligenceErrorHandler:
    @staticmethod
    async def handle_learner_memory_content_invalid_error(
        _request: Request, error: Exception
    ) -> JSONResponse:
        invalid = error if isinstance(error, LearnerMemoryContentInvalidError) else None
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                'code': 'validation_error',
                'message': (
                    invalid.message
                    if invalid is not None
                    else LearnerMemoryContentInvalidError.message
                ),
            },
        )

    @staticmethod
    async def handle_mentor_cursor_invalid_error(
        _request: Request, error: Exception
    ) -> JSONResponse:
        invalid = error if isinstance(error, MentorCursorInvalidError) else None
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                'code': 'validation_error',
                'message': (
                    invalid.message
                    if invalid is not None
                    else MentorCursorInvalidError.message
                ),
            },
        )

    @staticmethod
    def register(app: FastAPI) -> None:
        app.add_exception_handler(
            LearnerMemoryContentInvalidError,
            IntelligenceErrorHandler.handle_learner_memory_content_invalid_error,
        )
        app.add_exception_handler(
            MentorCursorInvalidError,
            IntelligenceErrorHandler.handle_mentor_cursor_invalid_error,
        )

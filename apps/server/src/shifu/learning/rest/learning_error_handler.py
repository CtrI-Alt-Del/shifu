from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from shifu.learning.core.domain.errors import (
    CurriculumGapError,
    PracticeDraftConflictError,
    PracticeDraftIncompleteError,
    PracticePhotoInvalidError,
    PracticePhotoTooLargeError,
)


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
    async def handle_practice_photo_invalid_error(
        _request: Request, error: Exception
    ) -> JSONResponse:
        invalid = error if isinstance(error, PracticePhotoInvalidError) else None
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                'code': 'malformed_photo',
                'message': (
                    invalid.message
                    if invalid is not None
                    else PracticePhotoInvalidError.message
                ),
            },
        )

    @staticmethod
    async def handle_practice_photo_too_large_error(
        _request: Request, error: Exception
    ) -> JSONResponse:
        too_large = error if isinstance(error, PracticePhotoTooLargeError) else None
        return JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={
                'code': 'photo_too_large',
                'message': (
                    too_large.message
                    if too_large is not None
                    else PracticePhotoTooLargeError.message
                ),
            },
        )

    @staticmethod
    async def handle_practice_draft_conflict_error(
        _request: Request, error: Exception
    ) -> JSONResponse:
        conflict = error if isinstance(error, PracticeDraftConflictError) else None
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                'code': 'practice_draft_conflict',
                'message': (
                    conflict.message
                    if conflict is not None
                    else PracticeDraftConflictError.message
                ),
            },
        )

    @staticmethod
    async def handle_practice_draft_incomplete_error(
        _request: Request, error: Exception
    ) -> JSONResponse:
        incomplete = error if isinstance(error, PracticeDraftIncompleteError) else None
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                'code': 'practice_draft_incomplete',
                'message': (
                    incomplete.message
                    if incomplete is not None
                    else PracticeDraftIncompleteError.message
                ),
            },
        )

    @staticmethod
    def register(app: FastAPI) -> None:
        app.add_exception_handler(
            CurriculumGapError,
            LearningErrorHandler.handle_curriculum_gap_error,
        )
        app.add_exception_handler(
            PracticeDraftConflictError,
            LearningErrorHandler.handle_practice_draft_conflict_error,
        )
        app.add_exception_handler(
            PracticeDraftIncompleteError,
            LearningErrorHandler.handle_practice_draft_incomplete_error,
        )
        app.add_exception_handler(
            PracticePhotoInvalidError,
            LearningErrorHandler.handle_practice_photo_invalid_error,
        )
        app.add_exception_handler(
            PracticePhotoTooLargeError,
            LearningErrorHandler.handle_practice_photo_too_large_error,
        )

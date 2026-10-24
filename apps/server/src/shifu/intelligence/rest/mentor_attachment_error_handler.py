from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from shifu.intelligence.core.domain.errors import (
    MentorAttachmentInvalidError,
    MentorAttachmentTooLargeError,
)


class MentorAttachmentErrorHandler:
    @staticmethod
    async def handle_invalid_error(_request: Request, error: Exception) -> JSONResponse:
        invalid = error if isinstance(error, MentorAttachmentInvalidError) else None
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                'code': 'malformed_attachment',
                'message': (
                    invalid.message
                    if invalid is not None
                    else 'O arquivo não é válido ou não é compatível.'
                ),
            },
        )

    @staticmethod
    async def handle_too_large_error(
        _request: Request, error: Exception
    ) -> JSONResponse:
        too_large = error if isinstance(error, MentorAttachmentTooLargeError) else None
        return JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={
                'code': 'attachment_too_large',
                'message': (
                    too_large.message
                    if too_large is not None
                    else MentorAttachmentTooLargeError.message
                ),
            },
        )

    @staticmethod
    def register(app: FastAPI) -> None:
        app.add_exception_handler(
            MentorAttachmentInvalidError,
            MentorAttachmentErrorHandler.handle_invalid_error,
        )
        app.add_exception_handler(
            MentorAttachmentTooLargeError,
            MentorAttachmentErrorHandler.handle_too_large_error,
        )

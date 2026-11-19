from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from shifu.communication.core.domain.errors import (
    InvalidPushSubscriptionError,
    PushUnavailableError,
)


class CommunicationErrorHandler:
    @staticmethod
    async def handle_push_unavailable_error(
        _request: Request, error: Exception
    ) -> JSONResponse:
        unavailable = error if isinstance(error, PushUnavailableError) else None
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                'code': 'push_unavailable',
                'message': (
                    unavailable.message
                    if unavailable is not None
                    else PushUnavailableError.message
                ),
            },
        )

    @staticmethod
    async def handle_invalid_push_subscription_error(
        _request: Request, error: Exception
    ) -> JSONResponse:
        invalid = error if isinstance(error, InvalidPushSubscriptionError) else None
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                'code': 'validation_error',
                'message': (
                    invalid.message
                    if invalid is not None
                    else InvalidPushSubscriptionError.message
                ),
            },
        )

    @staticmethod
    def register(app: FastAPI) -> None:
        app.add_exception_handler(
            PushUnavailableError,
            CommunicationErrorHandler.handle_push_unavailable_error,
        )
        app.add_exception_handler(
            InvalidPushSubscriptionError,
            CommunicationErrorHandler.handle_invalid_push_subscription_error,
        )

import re

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from shifu.identity.core.domain.errors import InvalidCredentialsError
from shifu.shared.core.domain.errors import (
	AppError,
	ConflictError,
	NotFoundError,
	ValidationError,
)


class AppErrorHandler:
    _IDENTITY_FAILURE_PATHS = frozenset(
        {'/identity/sign-in', '/identity/main-page-entries'}
    )

    @staticmethod
    def _error_code_from_class_name(class_name: str) -> str:
        name_without_error = class_name.replace('Error', '')
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', name_without_error).lower()
        return snake

    @staticmethod
    def _build_response(*, status_code: int, code: str, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={'code': code, 'message': message},
        )

    @staticmethod
    async def handle_invalid_credentials(
        request: Request, _error: Exception
    ) -> JSONResponse:
        if request.url.path == '/identity/sign-in':
            return AppErrorHandler._build_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code='invalid_credentials',
                message='O e-mail ou a senha são inválidos.',
            )
        return AppErrorHandler._build_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code='internal_error',
            message='Ocorreu um erro inesperado.',
        )

    @staticmethod
    async def handle_unexpected_error(
        request: Request, _error: Exception
    ) -> JSONResponse:
        if request.url.path in AppErrorHandler._IDENTITY_FAILURE_PATHS:
            return AppErrorHandler._build_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code='identity_unavailable',
                message='O serviço de identidade está temporariamente indisponível.',
            )
        return AppErrorHandler._build_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code='internal_error',
            message='Ocorreu um erro inesperado.',
        )

    @staticmethod
    async def handle_app_error(request: Request, _error: Exception) -> JSONResponse:
        if request.url.path in AppErrorHandler._IDENTITY_FAILURE_PATHS:
            return AppErrorHandler._build_response(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                code='identity_unavailable',
                message='O serviço de identidade está temporariamente indisponível.',
            )
        return AppErrorHandler._build_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code='internal_error',
            message='Ocorreu um erro inesperado.',
        )

    @staticmethod
    async def handle_not_found_error(
        request: Request, error: Exception
    ) -> JSONResponse:
        error_code = AppErrorHandler._error_code_from_class_name(
            type(error).__name__
        )
        return AppErrorHandler._build_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code=error_code,
            message=str(error),
        )

    @staticmethod
    async def handle_conflict_error(
        request: Request, error: Exception
    ) -> JSONResponse:
        error_code = AppErrorHandler._error_code_from_class_name(
            type(error).__name__
        )
        return AppErrorHandler._build_response(
            status_code=status.HTTP_409_CONFLICT,
            code=error_code,
            message=str(error),
        )

    @staticmethod
    async def handle_validation_error(
        request: Request, error: Exception
    ) -> JSONResponse:
        error_code = AppErrorHandler._error_code_from_class_name(
            type(error).__name__
        )
        return AppErrorHandler._build_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=error_code,
            message=str(error),
        )

    @staticmethod
    def register(app: FastAPI) -> None:
        app.add_exception_handler(
            InvalidCredentialsError,
            AppErrorHandler.handle_invalid_credentials,
        )
        app.add_exception_handler(
            NotFoundError, AppErrorHandler.handle_not_found_error
        )
        app.add_exception_handler(
            ConflictError, AppErrorHandler.handle_conflict_error
        )
        app.add_exception_handler(
            ValidationError, AppErrorHandler.handle_validation_error
        )
        app.add_exception_handler(AppError, AppErrorHandler.handle_app_error)
        app.add_exception_handler(
            Exception,
            AppErrorHandler.handle_unexpected_error,
        )

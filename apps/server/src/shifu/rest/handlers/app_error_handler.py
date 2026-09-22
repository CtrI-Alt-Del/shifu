from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from shifu.identity.core.domain.errors import InvalidCredentialsError
from shifu.shared.core.domain.errors import (
    AppError,
    AuthorizationError,
    NotFoundError,
    ServiceUnavailableError,
)


class AppErrorHandler:
    _IDENTITY_FAILURE_PATHS = frozenset(
        {'/identity/sign-in', '/identity/main-page-entries'}
    )

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
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code='service_unavailable',
            message='Serviço temporariamente indisponível.',
        )

    @staticmethod
    async def handle_not_found_error(
        _request: Request, error: Exception
    ) -> JSONResponse:
        not_found = error if isinstance(error, NotFoundError) else None
        return AppErrorHandler._build_response(
            status_code=status.HTTP_404_NOT_FOUND,
            code='not_found',
            message=(
                not_found.message
                if not_found is not None
                else 'Recurso não encontrado.'
            ),
        )

    @staticmethod
    async def handle_authorization_error(
        _request: Request, _error: Exception
    ) -> JSONResponse:
        return AppErrorHandler._build_response(
            status_code=status.HTTP_403_FORBIDDEN,
            code='forbidden',
            message='Acesso não autorizado.',
        )

    @staticmethod
    async def handle_service_unavailable(
        _request: Request, _error: Exception
    ) -> JSONResponse:
        return AppErrorHandler._build_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code='service_unavailable',
            message='Serviço temporariamente indisponível.',
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
    def register(app: FastAPI) -> None:
        app.add_exception_handler(
            InvalidCredentialsError,
            AppErrorHandler.handle_invalid_credentials,
        )
        app.add_exception_handler(
            NotFoundError,
            AppErrorHandler.handle_not_found_error,
        )
        app.add_exception_handler(
            AuthorizationError,
            AppErrorHandler.handle_authorization_error,
        )
        app.add_exception_handler(
            ServiceUnavailableError,
            AppErrorHandler.handle_service_unavailable,
        )
        app.add_exception_handler(AppError, AppErrorHandler.handle_app_error)
        app.add_exception_handler(
            Exception,
            AppErrorHandler.handle_unexpected_error,
        )

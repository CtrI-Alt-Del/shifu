import traceback
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from shifu.identity.core.domain.errors import InvalidCredentialsError
from shifu.shared.core.domain.errors import (
    AppError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from shifu.shared.core.interfaces.telemetry_provider import (
    SanitizedStackFrame,
    TelemetryEventInput,
)
from shifu.shared.rest.pipes.telemetry_pipe import TelemetryPipe


class AppErrorHandler:
    _IDENTITY_FAILURE_PATHS = frozenset(
        {'/identity/sign-in', '/identity/main-page-entries'}
    )
    _IDENTITY_PUBLIC_PATHS = frozenset(
        {
            '/identity/registrations',
            '/identity/pending-confirmations/status',
            '/identity/pending-confirmations/resend',
            '/identity/email-confirmations',
        }
    )

    @staticmethod
    def _build_response(*, status_code: int, code: str, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={'code': code, 'message': message},
        )

    @staticmethod
    def _emit(request: Request, event: TelemetryEventInput) -> None:
        request_id = TelemetryPipe.get_request_id(request)
        if request_id is not None:
            event['request_id'] = request_id
        TelemetryPipe.emit(
            TelemetryPipe.get_telemetry_provider(request),
            event,
        )

    @staticmethod
    def _stack_trace(error: Exception) -> list[SanitizedStackFrame]:
        frames: list[SanitizedStackFrame] = []
        for frame in traceback.extract_tb(error.__traceback__)[-20:]:
            file_name = frame.filename.replace('\\', '/').rsplit('/', 1)[-1]
            if not file_name:
                continue
            sanitized: SanitizedStackFrame = {'file': file_name}
            line_number = frame.lineno
            if isinstance(line_number, int) and line_number > 0:
                sanitized['line'] = line_number
            if frame.name:
                sanitized['function'] = frame.name
            frames.append(sanitized)
        return frames

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
        request: Request, error: Exception
    ) -> JSONResponse:
        AppErrorHandler._emit(
            request,
            {
                'level': 'ERROR',
                'event': 'error.unexpected',
                'operation': 'http.request',
                'result': 'failure',
                'error_code': 'internal_error',
                'exception_type': type(error).__name__,
                'stack_trace': AppErrorHandler._stack_trace(error),
            },
        )
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
                and not_found.message != 'Erro interno da aplicação.'
                else 'Recurso não encontrado.'
            ),
        )

    @staticmethod
    async def handle_conflict_error(
        _request: Request, error: Exception
    ) -> JSONResponse:
        conflict = error if isinstance(error, ConflictError) else None
        return AppErrorHandler._build_response(
            status_code=status.HTTP_409_CONFLICT,
            code='conflict',
            message=(
                conflict.message
                if conflict is not None
                else 'A solicitação conflita com o estado atual do recurso.'
            ),
        )

    @staticmethod
    async def handle_validation_error(
        _request: Request, error: Exception
    ) -> JSONResponse:
        validation = error if isinstance(error, ValidationError) else None
        return AppErrorHandler._build_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code='validation_error',
            message=(
                validation.message
                if validation is not None
                else 'Os dados enviados são inválidos.'
            ),
        )

    @staticmethod
    async def handle_authorization_error(
        request: Request, _error: Exception
    ) -> JSONResponse:
        AppErrorHandler._emit(
            request,
            {
                'level': 'WARNING',
                'event': 'auth.access.denied',
                'operation': 'auth.access',
                'result': 'failure',
                'error_code': 'forbidden',
            },
        )
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
    async def handle_request_validation_error(
        request: Request, _error: Exception
    ) -> JSONResponse:
        if request.url.path in AppErrorHandler._IDENTITY_PUBLIC_PATHS:
            return AppErrorHandler._build_response(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                code='invalid_input',
                message='Os dados enviados são inválidos.',
            )

        return AppErrorHandler._build_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code='validation_error',
            message='Os dados enviados são inválidos.',
        )

    @staticmethod
    async def handle_http_error(request: Request, error: Exception) -> JSONResponse:
        if not isinstance(error, StarletteHTTPException):
            AppErrorHandler._emit(
                request,
                {
                    'level': 'ERROR',
                    'event': 'error.unexpected',
                    'operation': 'http.request',
                    'result': 'failure',
                    'error_code': 'internal_error',
                    'exception_type': type(error).__name__,
                    'stack_trace': AppErrorHandler._stack_trace(error),
                },
            )
            return AppErrorHandler._build_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                code='internal_error',
                message='Ocorreu um erro inesperado.',
            )

        if error.status_code == status.HTTP_403_FORBIDDEN:
            AppErrorHandler._emit(
                request,
                {
                    'level': 'WARNING',
                    'event': 'auth.access.denied',
                    'operation': 'auth.access',
                    'result': 'failure',
                    'error_code': 'forbidden',
                },
            )

        detail = (
            cast('dict[str, object]', error.detail)
            if isinstance(error.detail, dict)
            else {}
        )
        code = detail.get('code')
        message = detail.get('message')
        if isinstance(code, str) and isinstance(message, str):
            return JSONResponse(
                status_code=error.status_code,
                content={'detail': {'code': code, 'message': message}},
                headers=error.headers,
            )

        errors = {
            status.HTTP_400_BAD_REQUEST: (
                'bad_request',
                'A solicitação enviada é inválida.',
            ),
            status.HTTP_401_UNAUTHORIZED: (
                'unauthorized',
                'Acesso não autorizado.',
            ),
            status.HTTP_403_FORBIDDEN: ('forbidden', 'Acesso não autorizado.'),
            status.HTTP_404_NOT_FOUND: ('not_found', 'Recurso não encontrado.'),
            status.HTTP_405_METHOD_NOT_ALLOWED: (
                'method_not_allowed',
                'O método HTTP não é permitido para este recurso.',
            ),
            status.HTTP_409_CONFLICT: (
                'conflict',
                'A solicitação conflita com o estado atual do recurso.',
            ),
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: (
                'content_too_large',
                'O conteúdo enviado é muito grande.',
            ),
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: (
                'unsupported_media_type',
                'O formato do conteúdo enviado não é compatível.',
            ),
            status.HTTP_422_UNPROCESSABLE_ENTITY: (
                'validation_error',
                'Os dados enviados são inválidos.',
            ),
            status.HTTP_429_TOO_MANY_REQUESTS: (
                'rate_limited',
                'Muitas solicitações. Aguarde e tente novamente.',
            ),
            status.HTTP_500_INTERNAL_SERVER_ERROR: (
                'internal_error',
                'Ocorreu um erro inesperado.',
            ),
            status.HTTP_503_SERVICE_UNAVAILABLE: (
                'service_unavailable',
                'Serviço temporariamente indisponível.',
            ),
        }
        code, message = errors.get(
            error.status_code,
            ('request_failed', 'Não foi possível concluir a solicitação.'),
        )
        return JSONResponse(
            status_code=error.status_code,
            content={'code': code, 'message': message},
            headers=error.headers,
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
            ConflictError,
            AppErrorHandler.handle_conflict_error,
        )
        app.add_exception_handler(
            ValidationError,
            AppErrorHandler.handle_validation_error,
        )
        app.add_exception_handler(
            AuthorizationError,
            AppErrorHandler.handle_authorization_error,
        )
        app.add_exception_handler(
            ServiceUnavailableError,
            AppErrorHandler.handle_service_unavailable,
        )
        app.add_exception_handler(
            RequestValidationError,
            AppErrorHandler.handle_request_validation_error,
        )
        app.add_exception_handler(
            StarletteHTTPException,
            AppErrorHandler.handle_http_error,
        )
        app.add_exception_handler(AppError, AppErrorHandler.handle_app_error)
        app.add_exception_handler(
            Exception,
            AppErrorHandler.handle_unexpected_error,
        )

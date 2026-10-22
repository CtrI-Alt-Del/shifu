from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request as FastAPIRequest, status
from pydantic import BaseModel, Field

from shifu.identity.core.domain.errors import InvalidCredentialsError
from shifu.identity.core.domain.structures import AuthCredentials, Authentication
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    PasswordHashingProvider,
)
from shifu.identity.core.use_cases import (
    IssuePendingConfirmationContextUseCase,
    SignInUseCase,
)
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.core.interfaces.telemetry_provider import (
    TelemetryEventInput,
    TelemetryProvider,
)
from shifu.shared.rest.pipes.telemetry_pipe import TelemetryPipe


class Request(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class Profile(BaseModel):
    account_id: str
    display_name: str
    email: str
    time_zone: str | None
    status: str
    created_at: str
    confirmed_at: str | None


class Response(BaseModel):
    profile: Profile
    access: Literal['protected', 'activation-only']
    access_version: int
    pending_handle: str | None = None


class SignInController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/sign-in',
            response_model=Response,
            response_model_exclude_none=True,
            status_code=status.HTTP_200_OK,
        )
        def _(
            http_request: FastAPIRequest,
            request: Request,
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            database: Annotated[
                IdentityDatabase,
                Depends(IdentityPipe.get_database),
            ],
            password_hashing_provider: Annotated[
                PasswordHashingProvider,
                Depends(IdentityPipe.get_password_hashing_provider),
            ],
            clock_provider: Annotated[
                ClockProvider,
                Depends(IdentityPipe.get_clock_provider),
            ],
            pending_handle_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_pending_confirmation_handle_provider),
            ],
            telemetry_provider: Annotated[
                TelemetryProvider | None,
                Depends(TelemetryPipe.get_telemetry_provider),
            ],
        ) -> Response:
            try:
                authentication = SignInUseCase(
                    database,
                    password_hashing_provider,
                ).execute(
                    AuthCredentials(email=request.email, password=request.password)
                )
            except (AuthorizationError, InvalidCredentialsError) as error:
                event: TelemetryEventInput = {
                    'level': 'WARNING',
                    'event': 'auth.login.refused',
                    'operation': 'auth.login',
                    'result': 'failure',
                    'error_code': (
                        'invalid_credentials'
                        if isinstance(error, InvalidCredentialsError)
                        else 'forbidden'
                    ),
                }
                TelemetryPipe.emit(
                    telemetry_provider,
                    SignInController._with_request_id(http_request, event),
                )
                raise
            pending_handle = (
                IssuePendingConfirmationContextUseCase(
                    identity_database=database,
                    clock_provider=clock_provider,
                    pending_confirmation_handle_provider=pending_handle_provider,
                ).execute(authentication.profile.account_id)
                if authentication.access.value == 'activation-only'
                else None
            )
            response = SignInController._to_response(authentication, pending_handle)
            TelemetryPipe.emit(
                telemetry_provider,
                SignInController._with_request_id(
                    http_request,
                    {
                        'level': 'INFO',
                        'event': 'auth.login.succeeded',
                        'operation': 'auth.login',
                        'result': 'success',
                    },
                ),
            )
            return response

    @staticmethod
    def _with_request_id(
        request: FastAPIRequest,
        event: TelemetryEventInput,
    ) -> TelemetryEventInput:
        request_id = TelemetryPipe.get_request_id(request)
        if request_id is not None:
            event['request_id'] = request_id
        return event

    @staticmethod
    def _to_response(
        authentication: Authentication,
        pending_handle: str | None,
    ) -> Response:
        profile = authentication.profile
        return Response(
            profile=Profile(
                account_id=profile.account_id,
                display_name=profile.display_name,
                email=profile.email,
                time_zone=profile.time_zone,
                status=profile.status.value,
                created_at=profile.created_at.isoformat(),
                confirmed_at=(
                    profile.confirmed_at.isoformat()
                    if profile.confirmed_at is not None
                    else None
                ),
            ),
            access=authentication.access.value,
            access_version=authentication.access_version,
            pending_handle=pending_handle,
        )

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

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
from shifu.shared.core.interfaces import ClockProvider


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
        ) -> Response:
            authentication = SignInUseCase(
                database,
                password_hashing_provider,
            ).execute(AuthCredentials(email=request.email, password=request.password))
            pending_handle = (
                IssuePendingConfirmationContextUseCase(
                    identity_database=database,
                    clock_provider=clock_provider,
                    pending_confirmation_handle_provider=pending_handle_provider,
                ).execute(authentication.profile.account_id)
                if authentication.access.value == 'activation-only'
                else None
            )
            return SignInController._to_response(authentication, pending_handle)

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

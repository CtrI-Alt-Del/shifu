from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, PlainSerializer, TypeAdapter

from shifu.identity.core.domain.structures import AuthCredentials
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    PasswordHashingProvider,
)
from shifu.identity.core.use_cases import (
    IssuePendingConfirmationContextUseCase,
    SignInUseCase,
    SignInWithPendingContextUseCase,
)
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.interfaces import ClockProvider


type IsoDatetime = Annotated[
    datetime,
    PlainSerializer(lambda value: value.isoformat(), return_type=str),
]


class Request(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class Profile(BaseModel):
    account_id: str
    display_name: str
    email: str
    time_zone: str | None
    status: str
    created_at: IsoDatetime
    confirmed_at: IsoDatetime | None


class Response(BaseModel):
    profile: Profile
    access: Literal['protected', 'activation-only']
    access_version: int
    pending_handle: str | None = None


_RESPONSE_ADAPTER = TypeAdapter(Response)


class SignInController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/sign-in',
            response_model=Response,
            response_model_exclude_none=True,
            status_code=200,
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
            authentication = SignInWithPendingContextUseCase(
                sign_in_use_case=SignInUseCase(database, password_hashing_provider),
                issue_pending_confirmation_context_use_case=(
                    IssuePendingConfirmationContextUseCase(
                        identity_database=database,
                        clock_provider=clock_provider,
                        pending_confirmation_handle_provider=pending_handle_provider,
                    )
                ),
            ).execute(AuthCredentials(email=request.email, password=request.password))
            return _RESPONSE_ADAPTER.validate_python(
                authentication,
                from_attributes=True,
            )

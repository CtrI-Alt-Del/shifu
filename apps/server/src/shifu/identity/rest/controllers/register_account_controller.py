import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from shifu.identity.core.domain.structures import AccountRegistration
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    ConfirmationDeliveryGateway,
    IdentityDatabase,
    PasswordHashingProvider,
)
from shifu.identity.core.use_cases import (
    QueueConfirmationDeliveryUseCase,
    RegisterAccountUseCase,
)
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


_EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    display_name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    password: str = Field(min_length=8)

    @field_validator('display_name')
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError('Informe seu nome.')

        return normalized

    @field_validator('email')
    @classmethod
    def normalize_and_validate_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not _EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError('Informe um e-mail válido.')

        return normalized


class Response(BaseModel):
    result: Literal['pending'] = 'pending'
    pending_handle: str
    is_decoy: bool


_RESPONSE_ADAPTER = TypeAdapter(Response)


class RegisterAccountController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/registrations',
            response_model=Response,
            status_code=202,
        )
        def _(
            request: Request,
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
            id_provider: Annotated[
                IdentifierProvider,
                Depends(IdentityPipe.get_identifier_provider),
            ],
            clock_provider: Annotated[
                ClockProvider,
                Depends(IdentityPipe.get_clock_provider),
            ],
            password_hashing_provider: Annotated[
                PasswordHashingProvider,
                Depends(IdentityPipe.get_password_hashing_provider),
            ],
            action_token_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_action_token_provider),
            ],
            pending_handle_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_pending_confirmation_handle_provider),
            ],
            gateway: Annotated[
                ConfirmationDeliveryGateway,
                Depends(IdentityPipe.get_confirmation_delivery_gateway),
            ],
        ) -> Response:
            result = RegisterAccountUseCase(
                identity_database=database,
                id_provider=id_provider,
                clock_provider=clock_provider,
                password_hashing_provider=password_hashing_provider,
                action_token_provider=action_token_provider,
                pending_confirmation_handle_provider=pending_handle_provider,
                queue_confirmation_delivery_use_case=QueueConfirmationDeliveryUseCase(
                    identity_database=database,
                    clock_provider=clock_provider,
                    delivery_gateway=gateway,
                ),
            ).execute(
                AccountRegistration.create(
                    display_name=request.display_name,
                    email=request.email,
                    password=request.password,
                )
            )
            return _RESPONSE_ADAPTER.validate_python(result, from_attributes=True)

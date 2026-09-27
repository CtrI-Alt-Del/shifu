import re
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from shifu.identity.core.domain.structures import PasswordRecoveryRequest
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    IdentityDatabase,
    PasswordRecoveryDeliveryGateway,
)
from shifu.identity.core.use_cases import RequestPasswordRecoveryUseCase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


_EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    email: str = Field(min_length=1)

    @field_validator('email')
    @classmethod
    def normalize_and_validate_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not _EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError('Informe um e-mail válido.')
        return normalized


class Response(BaseModel):
    recovery_handle: str
    is_decoy: bool


class RequestPasswordRecoveryController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/password-recovery-requests',
            response_model=Response,
            status_code=status.HTTP_202_ACCEPTED,
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
            action_token_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_action_token_provider),
            ],
            recovery_handle_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_recovery_handle_provider),
            ],
            gateway: Annotated[
                PasswordRecoveryDeliveryGateway,
                Depends(IdentityPipe.get_password_recovery_delivery_gateway),
            ],
        ) -> Response:
            result = RequestPasswordRecoveryUseCase(
                identity_database=database,
                id_provider=id_provider,
                clock_provider=clock_provider,
                action_token_provider=action_token_provider,
                recovery_handle_provider=recovery_handle_provider,
                delivery_gateway=gateway,
            ).execute(PasswordRecoveryRequest(email=request.email))
            return Response(
                recovery_handle=result.recovery_handle,
                is_decoy=result.is_decoy,
            )

import re
from datetime import datetime
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from shifu.identity.core.domain.structures import (
    AccountRegistration,
    AccountRegistrationResult,
)
from shifu.identity.core.domain.enums import (
    AccountConfirmationDeliveryStatus,
    ConfirmationDeliveryQueueStatus,
)
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    ConfirmationAccountActionTokensRepository,
    ConfirmationDeliveryGateway,
    ConfirmationDeliveryRequest,
    IdentityDatabase,
    PasswordHashingProvider,
)
from shifu.identity.core.use_cases import RegisterAccountUseCase
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
    result: Literal['pending']
    pending_handle: str


class RegisterAccountController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/registrations',
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
            ).execute(
                AccountRegistration.create(
                    display_name=request.display_name,
                    email=request.email,
                    password=request.password,
                )
            )
            delivery_request = RegisterAccountController._to_delivery_request(
                result=result,
                registration_email=request.email,
                registration_name=request.display_name,
            )
            if delivery_request is not None:
                delivery_result = gateway.queue(delivery_request)
                if (
                    delivery_result.status
                    is ConfirmationDeliveryQueueStatus.DELIVERY_UNAVAILABLE
                ):
                    RegisterAccountController._record_delivery_unavailable(
                        database,
                        result.identity_confirmation_id,
                        clock_provider.now(),
                    )
            return Response(result='pending', pending_handle=result.pending_handle)

    @staticmethod
    def _record_delivery_unavailable(
        database: IdentityDatabase,
        identity_confirmation_id: str | None,
        recorded_at: datetime,
    ) -> None:
        if identity_confirmation_id is None:
            return
        with database.transaction() as repositories:
            token_repository = cast(
                'ConfirmationAccountActionTokensRepository',
                repositories.account_action_tokens,
            )
            token = token_repository.find_by_id(identity_confirmation_id)
            if token is None:
                return
            if token.record_delivery_status(
                AccountConfirmationDeliveryStatus.DELIVERY_UNAVAILABLE,
                recorded_at,
            ):
                token_repository.update(token)

    @staticmethod
    def _to_delivery_request(
        *,
        result: AccountRegistrationResult,
        registration_email: str,
        registration_name: str,
    ) -> ConfirmationDeliveryRequest | None:
        if (
            result.account_id is None
            or result.identity_confirmation_id is None
            or result.communication_id is None
            or result.confirmation_token is None
            or result.confirmation_expires_at is None
        ):
            return None
        return ConfirmationDeliveryRequest(
            communication_id=result.communication_id,
            identity_confirmation_id=result.identity_confirmation_id,
            account_id=result.account_id,
            recipient_email=registration_email,
            recipient_name=registration_name,
            confirmation_token=result.confirmation_token,
            expires_at=result.confirmation_expires_at,
        )

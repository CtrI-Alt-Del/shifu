from datetime import datetime
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from shifu.identity.core.domain.enums import (
    AccountConfirmationDeliveryStatus,
    AccountStatus,
    ConfirmationDeliveryQueueStatus,
)
from shifu.identity.core.domain.structures import ResendConfirmationResult
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    ConfirmationAccountActionTokensRepository,
    ConfirmationDeliveryGateway,
    ConfirmationDeliveryRequest,
    IdentityDatabase,
)
from shifu.identity.core.use_cases import ResendEmailConfirmationUseCase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    pending_handle: str = Field(
        min_length=43,
        max_length=43,
        pattern=r'^[A-Za-z0-9_-]{43}$',
    )


class Response(BaseModel):
    result: Literal['accepted', 'cooldown']
    retry_after_seconds: int | None = None


class ResendEmailConfirmationController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/pending-confirmations/resend',
            response_model=Response,
            status_code=status.HTTP_200_OK,
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
            pending_handle_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_pending_confirmation_handle_provider),
            ],
            gateway: Annotated[
                ConfirmationDeliveryGateway,
                Depends(IdentityPipe.get_confirmation_delivery_gateway),
            ],
        ) -> Response:
            result = ResendEmailConfirmationUseCase(
                identity_database=database,
                id_provider=id_provider,
                clock_provider=clock_provider,
                action_token_provider=action_token_provider,
                pending_confirmation_handle_provider=pending_handle_provider,
            ).execute(request.pending_handle)
            delivery_request = ResendEmailConfirmationController._load_delivery_request(
                database=database,
                pending_handle=request.pending_handle,
                result=result,
            )
            if delivery_request is not None:
                delivery_result = gateway.queue(delivery_request)
                if (
                    delivery_result.status
                    is ConfirmationDeliveryQueueStatus.DELIVERY_UNAVAILABLE
                ):
                    ResendEmailConfirmationController._record_delivery_unavailable(
                        database,
                        result.identity_confirmation_id,
                        clock_provider.now(),
                    )
            return Response(
                result=result.result.value,
                retry_after_seconds=result.retry_after_seconds,
            )

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
    def _load_delivery_request(
        *,
        database: IdentityDatabase,
        pending_handle: str,
        result: ResendConfirmationResult,
    ) -> ConfirmationDeliveryRequest | None:
        if (
            result.identity_confirmation_id is None
            or result.communication_id is None
            or result.confirmation_token is None
            or result.confirmation_expires_at is None
        ):
            return None
        with database.transaction() as repositories:
            token_repository = cast(
                'ConfirmationAccountActionTokensRepository',
                repositories.account_action_tokens,
            )
            token = token_repository.find_by_id(result.identity_confirmation_id)
            if token is None or token.pending_handle_hash is None:
                return None
            account = repositories.accounts.find_by_id(token.account_id)
            if (
                account is None
                or account.status is not AccountStatus.PENDING_CONFIRMATION
            ):
                return None
            return ConfirmationDeliveryRequest(
                communication_id=result.communication_id,
                identity_confirmation_id=result.identity_confirmation_id,
                account_id=account.id,
                recipient_email=account.email,
                recipient_name=account.display_name,
                confirmation_token=result.confirmation_token,
                expires_at=result.confirmation_expires_at,
            )

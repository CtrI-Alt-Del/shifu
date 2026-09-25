from datetime import timedelta
from math import ceil
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountConfirmationDeliveryStatus,
    AccountStatus,
)
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    ConfirmationAccountActionTokensRepository,
    IdentityDatabase,
)
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.interfaces import ClockProvider


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    pending_handle: str = Field(
        min_length=43,
        max_length=43,
        pattern=r'^[A-Za-z0-9_-]{43}$',
    )


class Response(BaseModel):
    state: Literal['ready', 'cooldown', 'delivery_issue']
    retry_after_seconds: int | None = None


class GetPendingConfirmationStatusController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/pending-confirmations/status',
            response_model=Response,
            status_code=status.HTTP_200_OK,
        )
        def _(
            request: Request,
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
            clock_provider: Annotated[
                ClockProvider,
                Depends(IdentityPipe.get_clock_provider),
            ],
            pending_handle_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_pending_confirmation_handle_provider),
            ],
        ) -> Response:
            pending_handle_hash = pending_handle_provider.hash(request.pending_handle)
            now = clock_provider.now()
            with database.transaction() as repositories:
                token_repository = cast(
                    'ConfirmationAccountActionTokensRepository',
                    repositories.account_action_tokens,
                )
                token = token_repository.find_by_pending_handle_hash(
                    pending_handle_hash
                )
                if token is None:
                    return Response(state='delivery_issue')
                account = repositories.accounts.find_by_id(token.account_id)
                if (
                    account is None
                    or account.status is not AccountStatus.PENDING_CONFIRMATION
                ):
                    return Response(state='delivery_issue')
                latest_token = (
                    token_repository.find_latest_by_account_id_and_type(
                        account.id,
                        token.type,
                    )
                    or token
                )
                if latest_token.status is not AccountActionTokenStatus.PENDING:
                    return Response(state='delivery_issue')
                if latest_token.delivery_status in {
                    AccountConfirmationDeliveryStatus.DELIVERY_UNAVAILABLE,
                    AccountConfirmationDeliveryStatus.TEMPORARY_FAILURE,
                    AccountConfirmationDeliveryStatus.PERMANENT_FAILURE,
                    AccountConfirmationDeliveryStatus.EXHAUSTED,
                }:
                    return Response(state='delivery_issue')
                cooldown_ends_at = latest_token.issued_at + timedelta(seconds=60)
                if now < cooldown_ends_at:
                    return Response(
                        state='cooldown',
                        retry_after_seconds=max(
                            1,
                            ceil((cooldown_ends_at - now).total_seconds()),
                        ),
                    )
                return Response(state='ready')

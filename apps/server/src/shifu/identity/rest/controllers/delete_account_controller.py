from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from shifu.identity.core.domain.structures import DeleteAccountInput
from shifu.identity.core.interfaces import IdentityDatabase, PasswordHashingProvider
from shifu.identity.core.use_cases import DeleteAccountUseCase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    erasure_id: UUID = Field(strict=False)
    current_password: str = Field(min_length=1, max_length=256)
    confirmed: Literal[True]


class Response(BaseModel):
    state: Literal['closed']
    closed_at: datetime
    erasure: Literal['pending', 'completed']


class DeleteAccountController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post('/account-deletions', response_model=Response, status_code=202)
        def _(
            request: Request,
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            user: Annotated[
                AuthenticatedUser,
                Depends(IdentityPipe.get_authenticated_user_unscoped),
            ],
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
            clock: Annotated[ClockProvider, Depends(IdentityPipe.get_clock_provider)],
            hasher: Annotated[
                PasswordHashingProvider,
                Depends(IdentityPipe.get_password_hashing_provider),
            ],
        ) -> Response:
            result = DeleteAccountUseCase(database, clock, hasher).execute(
                user,
                DeleteAccountInput(
                    account_id=user.account_id,
                    erasure_id=request.erasure_id,
                    current_password=request.current_password,
                    confirmed=request.confirmed,
                ),
            )
            return Response(
                state=result.state,
                closed_at=result.closed_at,
                erasure=result.erasure,
            )

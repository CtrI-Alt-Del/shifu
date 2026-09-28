from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict

from shifu.identity.core.interfaces import ActionTokenProvider, IdentityDatabase
from shifu.identity.core.use_cases import ResolvePasswordResetLinkUseCase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.interfaces import ClockProvider


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid')

    token: str


class Response(BaseModel):
    result: Literal['valid', 'expired', 'used', 'invalid']


class ResolvePasswordResetLinkController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/password-reset-links/status',
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
            action_token_provider: Annotated[
                ActionTokenProvider,
                Depends(IdentityPipe.get_action_token_provider),
            ],
        ) -> Response:
            result = ResolvePasswordResetLinkUseCase(
                identity_database=database,
                clock_provider=clock_provider,
                action_token_provider=action_token_provider,
            ).execute(request.token)
            return Response(result=result.result)

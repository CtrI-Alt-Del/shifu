from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from shifu.identity.core.domain.structures import PasswordChangeRequest
from shifu.identity.core.interfaces import IdentityDatabase, PasswordHashingProvider
from shifu.identity.core.use_cases import ChangePasswordUseCase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    current_password: str
    new_password: str


class Response(BaseModel):
    changed: Literal[True] = True


class ChangePasswordController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post('/accounts/me/password', response_model=Response, status_code=200)
        def _(
            request: Request,
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            user: Annotated[
                AuthenticatedUser, Depends(IdentityPipe.get_authenticated_user)
            ],
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
            clock: Annotated[ClockProvider, Depends(IdentityPipe.get_clock_provider)],
            hasher: Annotated[
                PasswordHashingProvider,
                Depends(IdentityPipe.get_password_hashing_provider),
            ],
        ) -> Response:
            ChangePasswordUseCase(database, clock, hasher).execute(
                user,
                PasswordChangeRequest(
                    current_password=request.current_password,
                    new_password=request.new_password,
                ),
            )
            return Response()

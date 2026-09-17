from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.domain.structures import AuthenticatedUser


class Response(BaseModel):
    account_id: str
    display_name: str
    time_zone: str | None


class GetCurrentSessionController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get('/session', response_model=Response, status_code=status.HTTP_200_OK)
        def _(
            user: Annotated[
                AuthenticatedUser,
                Depends(IdentityPipe.get_authenticated_user),
            ],
        ) -> Response | JSONResponse:
            return Response(
                account_id=user.account_id,
                display_name=user.display_name,
                time_zone=user.time_zone,
            )

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, TypeAdapter

from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.domain.structures import AuthenticatedUser


class Response(BaseModel):
    account_id: str
    display_name: str
    time_zone: str | None


_RESPONSE_ADAPTER = TypeAdapter(Response)


class GetCurrentSessionController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get('/session', response_model=Response, status_code=200)
        def _(
            user: Annotated[
                AuthenticatedUser,
                Depends(IdentityPipe.get_authenticated_user),
            ],
        ) -> Response:
            return _RESPONSE_ADAPTER.validate_python(user, from_attributes=True)

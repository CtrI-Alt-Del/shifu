from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, TypeAdapter

from shifu.identity.core.domain.enums import AccountAppearance
from shifu.identity.core.interfaces import IdentityDatabase
from shifu.identity.core.use_cases import GetAccountProfileUseCase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.domain.structures import AuthenticatedUser


class Response(BaseModel):
    account_id: str
    display_name: str
    time_zone: str | None
    appearance: AccountAppearance


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
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
        ) -> Response:
            profile = GetAccountProfileUseCase(database).execute(user)
            return _RESPONSE_ADAPTER.validate_python(profile, from_attributes=True)

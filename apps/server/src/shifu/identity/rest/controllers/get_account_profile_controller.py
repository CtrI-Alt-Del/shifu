from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, TypeAdapter

from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.core.interfaces import IdentityDatabase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.identity.core.use_cases import GetAccountProfileUseCase


class Response(BaseModel):
    account_id: str
    display_name: str
    email: str
    time_zone: str | None
    status: AccountStatus
    created_at: datetime
    confirmed_at: datetime | None


_RESPONSE_ADAPTER = TypeAdapter(Response)


class GetAccountProfileController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get('/accounts/me', response_model=Response, status_code=200)
        def _(
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            user: Annotated[
                AuthenticatedUser, Depends(IdentityPipe.get_authenticated_user)
            ],
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
        ) -> Response:
            profile = GetAccountProfileUseCase(database).execute(user)
            return _RESPONSE_ADAPTER.validate_python(profile, from_attributes=True)

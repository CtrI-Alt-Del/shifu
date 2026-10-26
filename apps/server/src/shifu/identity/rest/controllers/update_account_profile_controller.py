from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, TypeAdapter

from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.core.interfaces import IdentityDatabase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.identity.core.domain.structures import AccountProfileUpdate
from shifu.identity.core.use_cases import UpdateAccountProfileUseCase
from shifu.shared.core.interfaces import ClockProvider


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    display_name: str
    time_zone: str


class Response(BaseModel):
    account_id: str
    display_name: str
    email: str
    time_zone: str | None
    status: AccountStatus
    created_at: datetime
    confirmed_at: datetime | None


_RESPONSE_ADAPTER = TypeAdapter(Response)


class UpdateAccountProfileController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.patch('/accounts/me', response_model=Response, status_code=200)
        def _(
            request: Request,
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            user: Annotated[
                AuthenticatedUser, Depends(IdentityPipe.get_authenticated_user)
            ],
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
            clock: Annotated[ClockProvider, Depends(IdentityPipe.get_clock_provider)],
        ) -> Response:
            profile = UpdateAccountProfileUseCase(database, clock).execute(
                user,
                AccountProfileUpdate(
                    display_name=request.display_name, time_zone=request.time_zone
                ),
            )
            return _RESPONSE_ADAPTER.validate_python(profile, from_attributes=True)

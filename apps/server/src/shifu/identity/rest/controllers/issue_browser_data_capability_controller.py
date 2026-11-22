from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette.responses import Response as HttpResponse

from shifu.identity.core.use_cases import IssueBrowserDataCapabilityUseCase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.identity.core.interfaces import IdentityDatabase


class Response(BaseModel):
    capability: str


class IssueBrowserDataCapabilityController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/browser-data-capabilities',
            response_model=Response,
            status_code=201,
        )
        def _(
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            user: Annotated[
                AuthenticatedUser, Depends(IdentityPipe.get_authenticated_user)
            ],
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
            clock: Annotated[ClockProvider, Depends(IdentityPipe.get_clock_provider)],
            response: HttpResponse,
        ) -> Response:
            response.headers['Cache-Control'] = 'no-store'
            capability = IssueBrowserDataCapabilityUseCase(database, clock).execute(
                user
            )
            return Response(capability=capability)

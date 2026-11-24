from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import Response as HttpResponse

from shifu.identity.core.interfaces import IdentityDatabase
from shifu.identity.core.use_cases import ValidateBrowserDataCapabilityUseCase
from shifu.identity.pipes import IdentityPipe


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    capability: str = Field(min_length=1, max_length=128)


class Response(BaseModel):
    state: Literal['active', 'revoked']


class ValidateBrowserDataCapabilityController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/browser-data-validations', response_model=Response, status_code=200
        )
        def _(
            request: Request,
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
            response: HttpResponse,
        ) -> Response:
            response.headers['Cache-Control'] = 'no-store'
            status = ValidateBrowserDataCapabilityUseCase(database).execute(
                request.capability
            )
            return Response(state=status.state)

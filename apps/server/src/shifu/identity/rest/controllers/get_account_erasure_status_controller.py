from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from starlette.responses import Response as HttpResponse

from shifu.identity.core.interfaces import IdentityDatabase
from shifu.identity.core.use_cases import GetAccountErasureStatusUseCase
from shifu.identity.pipes import IdentityPipe


class Response(BaseModel):
    state: Literal['closed']
    closed_at: datetime
    erasure: Literal['pending', 'completed']


class GetAccountErasureStatusController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/internal/account-erasures/{erasure_id}/status',
            response_model=Response,
            status_code=200,
        )
        def _(
            erasure_id: UUID,
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
            response: HttpResponse,
        ) -> Response:
            response.headers['Cache-Control'] = 'no-store'
            result = GetAccountErasureStatusUseCase(database).execute(erasure_id)
            if result is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={'code': 'not_found', 'message': 'Recurso não encontrado.'},
                )
            return Response(
                state=result.state,
                closed_at=result.closed_at,
                erasure=result.erasure,
            )

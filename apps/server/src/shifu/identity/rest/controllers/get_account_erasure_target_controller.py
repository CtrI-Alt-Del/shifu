from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from starlette.responses import Response as HttpResponse

from shifu.identity.core.interfaces import IdentityDatabase
from shifu.identity.pipes import IdentityPipe


class Response(BaseModel):
    account_id: str
    erasure_id: UUID


class GetAccountErasureTargetController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get(
            '/internal/account-erasures/{erasure_id}/target',
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
            with database.transaction() as repositories:
                account_id = repositories.account_erasures.find_account_id(erasure_id)
            if account_id is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={'code': 'not_found', 'message': 'Recurso não encontrado.'},
                )
            return Response(account_id=account_id, erasure_id=erasure_id)

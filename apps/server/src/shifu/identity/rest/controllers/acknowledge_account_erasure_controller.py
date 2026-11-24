from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from shifu.identity.core.interfaces import IdentityDatabase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.interfaces import ClockProvider


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    participant: str = Field(min_length=1, max_length=80)


class Response(BaseModel):
    acknowledged: bool = True


class AcknowledgeAccountErasureController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/internal/account-erasures/{erasure_id}/acknowledgements',
            response_model=Response,
            status_code=200,
        )
        def _(
            erasure_id: UUID,
            request: Request,
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
            clock: Annotated[ClockProvider, Depends(IdentityPipe.get_clock_provider)],
        ) -> Response:
            with database.transaction() as repositories:
                acknowledged = repositories.account_erasures.acknowledge(
                    erasure_id,
                    request.participant,
                    acknowledged_at=clock.now(),
                )
            if not acknowledged:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={'code': 'not_found', 'message': 'Recurso não encontrado.'},
                )
            return Response()

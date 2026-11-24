from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import Response as HttpResponse

from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.core.interfaces import IdentityDatabase
from shifu.identity.pipes import IdentityPipe


class Request(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    account_id: str = Field(min_length=1, max_length=26)
    access_version: int = Field(ge=1)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)


class AccountActivityAdmissionController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/internal/account-activity-admissions',
            status_code=204,
        )
        def _(
            request: Request,
            _: Annotated[None, Depends(IdentityPipe.require_bff)],
            database: Annotated[IdentityDatabase, Depends(IdentityPipe.get_database)],
            response: HttpResponse,
        ) -> None:
            response.headers['Cache-Control'] = 'no-store'
            with database.transaction() as repositories:
                account = repositories.accounts.find_by_id(request.account_id)
                if account is None or account.status is not AccountStatus.ACTIVE:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail={
                            'code': 'unauthorized',
                            'message': 'Acesso não autorizado.',
                        },
                    )
                accepts_activity = (
                    account.access_version == request.access_version
                    if request.session_id is None
                    else account.accepts_access(
                        request.session_id,
                        request.access_version,
                    )
                )
                if not accepts_activity:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail={
                            'code': 'unauthorized',
                            'message': 'Acesso não autorizado.',
                        },
                    )

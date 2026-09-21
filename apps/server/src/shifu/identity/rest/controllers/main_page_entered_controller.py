from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from shifu.identity.core.interfaces import IdentityDatabase
from shifu.identity.core.use_cases import PublishMainPageEnteredUseCase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class MainPageEnteredController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post(
            '/main-page-entries',
            response_model=None,
            status_code=status.HTTP_202_ACCEPTED,
        )
        def _(
            user: Annotated[
                AuthenticatedUser,
                Depends(IdentityPipe.get_authenticated_user),
            ],
            database: Annotated[
                IdentityDatabase,
                Depends(IdentityPipe.get_database),
            ],
            identifier_provider: Annotated[
                IdentifierProvider,
                Depends(IdentityPipe.get_identifier_provider),
            ],
            clock_provider: Annotated[
                ClockProvider,
                Depends(IdentityPipe.get_clock_provider),
            ],
        ) -> Response:
            PublishMainPageEnteredUseCase(
                database,
                identifier_provider,
                clock_provider,
            ).execute(user.account_id)
            return Response(status_code=status.HTTP_202_ACCEPTED)

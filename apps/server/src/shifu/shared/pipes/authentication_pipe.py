from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import AuthenticationProvider
from shifu.shared.pipes.shared_pipe import SharedPipe


class AuthenticationPipe:
    @staticmethod
    def get_authentication_provider(request: Request) -> AuthenticationProvider:
        return request.app.state.authentication_provider

    @staticmethod
    def get_authenticated_user(
        user: Annotated[
            AuthenticatedUser,
            Depends(SharedPipe.get_authenticated_user),
        ],
    ) -> AuthenticatedUser:
        return user

    @staticmethod
    def _unauthorized() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                'code': 'unauthorized',
                'message': 'Acesso não autorizado.',
            },
        )

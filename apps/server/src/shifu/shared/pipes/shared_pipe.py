from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import AuthenticationProvider


_BEARER_SCHEME = HTTPBearer(auto_error=False)


class SharedPipe:
    @staticmethod
    def get_authentication_provider(request: Request) -> AuthenticationProvider:
        return request.app.state.authentication_provider

    @staticmethod
    def get_authenticated_user(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(_BEARER_SCHEME),
        ],
        provider: Annotated[
            AuthenticationProvider,
            Depends(get_authentication_provider),
        ],
    ) -> AuthenticatedUser:
        if credentials is None or credentials.scheme.lower() != 'bearer':
            raise SharedPipe._unauthorized()
        try:
            return provider.authenticate(credentials.credentials)
        except AuthorizationError as error:
            raise SharedPipe._unauthorized() from error

    @staticmethod
    def _unauthorized() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                'code': 'unauthorized',
                'message': 'Acesso não autorizado.',
            },
        )

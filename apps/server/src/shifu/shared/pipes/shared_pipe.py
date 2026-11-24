from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    AccountActivityProvider,
    AuthenticationProvider,
    ClockProvider,
    IdentifierProvider,
)
from shifu.shared.providers.system_clock_provider import SystemClockProvider


_BEARER_SCHEME = HTTPBearer(auto_error=False)


class SharedPipe:
    @staticmethod
    def get_authentication_provider(request: Request) -> AuthenticationProvider:
        return request.app.state.authentication_provider

    @staticmethod
    def get_account_activity_provider(request: Request) -> AccountActivityProvider:
        return request.app.state.account_activity_provider

    @staticmethod
    def get_identifier_provider(request: Request) -> IdentifierProvider:
        return request.app.state.identifier_provider

    @staticmethod
    def get_clock_provider() -> ClockProvider:
        return SystemClockProvider()

    @staticmethod
    async def get_authenticated_user(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(_BEARER_SCHEME),
        ],
        provider: Annotated[
            AuthenticationProvider,
            Depends(get_authentication_provider),
        ],
        activity_provider: Annotated[
            AccountActivityProvider,
            Depends(get_account_activity_provider),
        ],
    ) -> AsyncIterator[AuthenticatedUser]:
        if credentials is None or credentials.scheme.lower() != 'bearer':
            raise SharedPipe._unauthorized()
        try:
            user = provider.authenticate(credentials.credentials)
        except AuthorizationError as error:
            raise SharedPipe._unauthorized() from error

        stack = AsyncExitStack()
        try:
            await stack.enter_async_context(
                activity_provider.async_activity(user.account_id, actor=user)
            )
        except AuthorizationError as error:
            await stack.aclose()
            raise SharedPipe._unauthorized() from error
        try:
            yield user
        finally:
            await stack.aclose()

    @staticmethod
    def get_authenticated_user_unscoped(
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

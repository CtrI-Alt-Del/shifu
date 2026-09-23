import secrets
from typing import Annotated, cast

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shifu.identity.core.interfaces import IdentityDatabase
from shifu.identity.core.interfaces import (
    ActionTokenProvider,
    ConfirmationDeliveryGateway,
)
from shifu.identity.providers.auth.jwt.jwks.jwks_jwt_authentication_provider import (
    JwksJwtAuthenticationProvider,
)
from shifu.identity.providers.auth.password_hashing.argon2id_hash_provider import (
    Argon2idHashProvider,
)
from shifu.identity.providers.security import PendingConfirmationHandleProvider
from shifu.shared.constants import ENVIRONMENT
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import (
    AuthenticationProvider,
    ClockProvider,
    IdentifierProvider,
)
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider


_BEARER_SCHEME = HTTPBearer(auto_error=False)


class IdentityPipe:
    @staticmethod
    def require_bff(
        x_shifu_bff_secret: Annotated[str | None, Header()] = None,
    ) -> None:
        if not x_shifu_bff_secret or not secrets.compare_digest(
            x_shifu_bff_secret,
            ENVIRONMENT.bff_shared_secret,
        ):
            raise IdentityPipe._unauthorized()

    @staticmethod
    def get_database(request: Request) -> IdentityDatabase:
        return request.app.state.identity_database

    @staticmethod
    def get_password_hashing_provider() -> Argon2idHashProvider:
        return Argon2idHashProvider()

    @staticmethod
    def get_action_token_provider() -> ActionTokenProvider:
        return PendingConfirmationHandleProvider()

    @staticmethod
    def get_pending_confirmation_handle_provider() -> ActionTokenProvider:
        return PendingConfirmationHandleProvider()

    @staticmethod
    def get_confirmation_delivery_gateway(
        request: Request,
    ) -> ConfirmationDeliveryGateway:
        return cast(
            'ConfirmationDeliveryGateway',
            request.app.state.confirmation_delivery_gateway,
        )

    @staticmethod
    def get_authentication_provider(request: Request) -> AuthenticationProvider:
        return JwksJwtAuthenticationProvider(
            identity_database=IdentityPipe.get_database(request),
            jwks_url=ENVIRONMENT.auth_jwks_url,
            issuer=ENVIRONMENT.auth_issuer,
            audience=ENVIRONMENT.auth_audience,
        )

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
            raise IdentityPipe._unauthorized()
        try:
            return provider.authenticate(credentials.credentials)
        except AuthorizationError as error:
            raise IdentityPipe._unauthorized() from error

    @staticmethod
    def _unauthorized() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                'code': 'unauthorized',
                'message': 'Acesso não autorizado.',
            },
        )

    @staticmethod
    def get_identifier_provider() -> IdentifierProvider:
        return SystemIdentifierProvider()

    @staticmethod
    def get_clock_provider() -> ClockProvider:
        return SystemClockProvider()

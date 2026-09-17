import json
import time
from collections.abc import Mapping
from threading import Lock
from typing import NoReturn, cast
from urllib.error import URLError
from urllib.request import Request, urlopen

import jwt

from shifu.identity.core.interfaces import IdentityDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser


class JwksJwtAuthenticationProvider:
    _CACHE_TTL_SECONDS: float = 60.0
    _REQUEST_TIMEOUT_SECONDS: float = 2.0

    def __init__(
        self,
        identity_database: IdentityDatabase,
        jwks_url: str,
        issuer: str,
        audience: str,
        request_timeout_seconds: float = _REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._identity_database: IdentityDatabase = identity_database
        self._jwks_url: str = jwks_url
        self._issuer: str = issuer
        self._audience: str = audience
        self._request_timeout_seconds: float = request_timeout_seconds
        self._keys: dict[str, jwt.PyJWK] = {}
        self._keys_expires_at: float = 0.0
        self._cache_lock: Lock = Lock()

    def authenticate(self, access_token: str) -> AuthenticatedUser:
        try:
            header = jwt.get_unverified_header(access_token)
            if header.get('alg') != 'EdDSA':
                self._reject()
            key_id = header.get('kid')
            if not isinstance(key_id, str) or not key_id:
                self._reject()

            signing_key = self._get_signing_key(key_id)
            claims = jwt.decode(
                access_token,
                signing_key,
                algorithms=['EdDSA'],
                audience=self._audience,
                issuer=self._issuer,
                options={
                    'require': [
                        'iss',
                        'aud',
                        'sub',
                        'iat',
                        'exp',
                        'jti',
                        'sid',
                        'access_version',
                    ]
                },
            )
            self._validate_claims(claims)
            account_id = cast('str', claims['sub'])
            access_version = cast('int', claims['access_version'])
            with self._identity_database.transaction() as repositories:
                account = repositories.accounts.find_by_id(account_id)

            if (
                account is None
                or account.status.value != 'active'
                or account.access_version != access_version
            ):
                self._reject()

            return AuthenticatedUser(
                account_id=account.id,
                display_name=account.display_name,
                time_zone=account.time_zone,
            )
        except AuthorizationError:
            raise
        except Exception as error:
            raise AuthorizationError from error

    def _get_signing_key(self, key_id: str) -> jwt.PyJWK:
        now = time.monotonic()
        with self._cache_lock:
            if now >= self._keys_expires_at or key_id not in self._keys:
                self._keys = self._fetch_keys()
                self._keys_expires_at = now + self._CACHE_TTL_SECONDS
            signing_key = self._keys.get(key_id)

        if signing_key is None:
            raise AuthorizationError
        return signing_key

    @staticmethod
    def _reject() -> NoReturn:
        raise AuthorizationError

    def _fetch_keys(self) -> dict[str, jwt.PyJWK]:
        request = Request(  # noqa: S310 - URL is trusted auth configuration.
            self._jwks_url,
            headers={'Accept': 'application/json'},
            method='GET',
        )
        try:
            with urlopen(  # noqa: S310 - URL is trusted auth configuration.
                request,
                timeout=self._request_timeout_seconds,
            ) as response:
                document_value: object = json.loads(response.read(1_000_000))
        except (OSError, URLError, ValueError) as error:
            raise AuthorizationError from error

        if not isinstance(document_value, Mapping):
            raise AuthorizationError
        document = cast('Mapping[str, object]', document_value)
        raw_keys = document.get('keys')
        if not isinstance(raw_keys, list):
            raise AuthorizationError

        keys: dict[str, jwt.PyJWK] = {}
        for raw_key in cast('list[object]', raw_keys):
            if not isinstance(raw_key, Mapping):
                continue
            typed_raw_key = cast('Mapping[str, object]', raw_key)
            key_id = typed_raw_key.get('kid')
            if not isinstance(key_id, str) or not key_id:
                continue
            try:
                jwk = jwt.PyJWK.from_dict(dict(typed_raw_key))
            except (TypeError, ValueError, jwt.PyJWTError):
                continue
            if jwk.algorithm_name != 'EdDSA':
                continue
            keys[key_id] = jwk

        if not keys:
            raise AuthorizationError
        return keys

    @staticmethod
    def _validate_claims(claims: Mapping[str, object]) -> None:
        for claim_name in ('sub', 'jti', 'sid'):
            value = claims.get(claim_name)
            if not isinstance(value, str) or not value:
                raise AuthorizationError

        for claim_name in ('iat', 'exp', 'access_version'):
            value = claims.get(claim_name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise AuthorizationError

            access_version = cast('int', claims['access_version'])
        if access_version < 1:
            raise AuthorizationError

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenStatus,
    AccountActionTokenType,
)
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.pipes import IdentityPipe
from shifu.fakers.identity.entities import AccountFaker
from shifu.shared.constants import ENVIRONMENT

if TYPE_CHECKING:
    from httpx import Response

    from tests.fixtures.postgres_fixture import PostgresDatabase


class _FixedClockProvider:
    def __init__(self, current: datetime) -> None:
        self._current = current

    def now(self) -> datetime:
        return self._current


class _FixedTokenProvider:
    @staticmethod
    def hash(token: str) -> str:
        return sha256(token.encode('utf-8')).hexdigest()


class TestResolvePasswordResetLinkController:
    def test_status_requires_bff_protection_and_returns_invalid_for_malformed_token(
        self,
        client: TestClient,
    ) -> None:
        unauthorized = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/password-reset-links/status',
                headers={'x-shifu-bff-secret': ''},
                json={'token': 'A' * 43},
            ),
        )
        malformed = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/password-reset-links/status',
                json={'token': 'malformed token'},
            ),
        )

        assert unauthorized.status_code == 401
        assert malformed.status_code == 200
        assert malformed.json() == {'result': 'invalid'}

    def test_status_resolves_only_safe_results_without_mutating_the_token(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        tokens = {
            'valid': 'A' * 43,
            'expired': 'B' * 43,
            'used': 'C' * 43,
            'invalidated': 'D' * 43,
        }
        database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            account = AccountFaker.fake(created_at=now, updated_at=now)
            repositories.accounts.add(account)
            for identifier, (name, raw_token) in enumerate(tokens.items(), start=1):
                repositories.account_action_tokens.add(
                    AccountActionToken(
                        id=f'{identifier:024d}',
                        account_id=account.id,
                        type=AccountActionTokenType.PASSWORD_RECOVERY,
                        status={
                            'valid': AccountActionTokenStatus.PENDING,
                            'expired': AccountActionTokenStatus.PENDING,
                            'used': AccountActionTokenStatus.USED,
                            'invalidated': AccountActionTokenStatus.INVALIDATED,
                        }[name],
                        token_hash=_FixedTokenProvider.hash(raw_token),
                        issued_at=now - timedelta(hours=2),
                        expires_at=(
                            now + timedelta(hours=1) if name != 'expired' else now
                        ),
                        updated_at=now,
                        communication_id=f'{identifier + 10:024d}',
                    )
                )

        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_action_token_provider] = lambda: (
            _FixedTokenProvider()
        )
        app.dependency_overrides[IdentityPipe.get_clock_provider] = lambda: (
            _FixedClockProvider(now)
        )
        with TestClient(
            app,
            headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
        ) as client:
            results = {
                name: cast(
                    'Response',
                    client.post(  # pyright: ignore[reportUnknownMemberType]
                        '/identity/password-reset-links/status',
                        json={'token': raw_token},
                    ),
                ).json()
                for name, raw_token in {**tokens, 'unknown': 'E' * 43}.items()
            }

        assert results == {
            'valid': {'result': 'valid'},
            'expired': {'result': 'expired'},
            'used': {'result': 'used'},
            'invalidated': {'result': 'invalid'},
            'unknown': {'result': 'invalid'},
        }
        with database.transaction() as repositories:
            expired = repositories.account_action_tokens.find_by_hash(
                _FixedTokenProvider.hash(tokens['expired'])
            )
            assert expired is not None
            assert expired.status is AccountActionTokenStatus.PENDING

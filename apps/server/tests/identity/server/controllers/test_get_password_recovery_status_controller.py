from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.identity.core.domain.entities import AccountActionToken
from shifu.identity.core.domain.enums import (
    AccountActionTokenDeliveryStatus,
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


_RECOVERY_TOKEN_HASH = 'recovery-token-hash'
_COOLDOWN_TOKEN_HASH = 'cooldown-token-hash'


class _FixedClockProvider:
    def __init__(self, current: datetime) -> None:
        self._current = current

    def now(self) -> datetime:
        return self._current


class _FixedHandleProvider:
    @staticmethod
    def hash(handle: str) -> str:
        return sha256(handle.encode('utf-8')).hexdigest()


class TestGetPasswordRecoveryStatusController:
    def test_status_requires_bff_protection(self, client: TestClient) -> None:
        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/password-recoveries/status',
                headers={'x-shifu-bff-secret': ''},
                json={'recovery_handle': 'opaque-handle'},
            ),
        )

        assert response.status_code == 401

    def test_unknown_and_terminal_contexts_have_the_same_safe_shape(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        terminal_handle = 'terminal-handle'
        database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            account = AccountFaker.fake(
                email='status@example.com',
                created_at=now,
                updated_at=now,
            )
            repositories.accounts.add(account)
            repositories.account_action_tokens.add(
                AccountActionToken(
                    id='00000000000000000000000001',
                    account_id=account.id,
                    type=AccountActionTokenType.PASSWORD_RECOVERY,
                    status=AccountActionTokenStatus.PENDING,
                    token_hash=_RECOVERY_TOKEN_HASH,
                    issued_at=now - timedelta(minutes=2),
                    expires_at=now + timedelta(hours=1),
                    updated_at=now,
                    communication_id='00000000000000000000000002',
                    pending_handle_hash=_FixedHandleProvider.hash(terminal_handle),
                    delivery_status=AccountActionTokenDeliveryStatus.PERMANENT_FAILURE,
                )
            )

        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_clock_provider] = lambda: (
            _FixedClockProvider(now)
        )
        app.dependency_overrides[IdentityPipe.get_recovery_handle_provider] = lambda: (
            _FixedHandleProvider()
        )
        with TestClient(
            app,
            headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
        ) as client:
            unknown = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/password-recoveries/status',
                    json={'recovery_handle': 'unknown-handle'},
                ),
            )
            terminal = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/password-recoveries/status',
                    json={'recovery_handle': terminal_handle},
                ),
            )

        assert unknown.status_code == terminal.status_code == 200
        assert (
            unknown.json()
            == terminal.json()
            == {
                'state': 'delivery_issue',
                'retry_after_seconds': None,
            }
        )

    def test_valid_context_returns_only_cooldown_state_and_retry_seconds(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        handle = 'cooldown-handle'
        database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            account = AccountFaker.fake(
                email='cooldown@example.com',
                created_at=now,
                updated_at=now,
            )
            repositories.accounts.add(account)
            repositories.account_action_tokens.add(
                AccountActionToken(
                    id='00000000000000000000000003',
                    account_id=account.id,
                    type=AccountActionTokenType.PASSWORD_RECOVERY,
                    status=AccountActionTokenStatus.PENDING,
                    token_hash=_COOLDOWN_TOKEN_HASH,
                    issued_at=now - timedelta(seconds=20),
                    expires_at=now + timedelta(hours=1),
                    updated_at=now,
                    communication_id='00000000000000000000000004',
                    pending_handle_hash=_FixedHandleProvider.hash(handle),
                )
            )

        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_clock_provider] = lambda: (
            _FixedClockProvider(now)
        )
        app.dependency_overrides[IdentityPipe.get_recovery_handle_provider] = lambda: (
            _FixedHandleProvider()
        )
        with TestClient(
            app,
            headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
        ) as client:
            response = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/password-recoveries/status',
                    json={'recovery_handle': handle},
                ),
            )

        assert response.status_code == 200
        assert response.json() == {'state': 'cooldown', 'retry_after_seconds': 40}

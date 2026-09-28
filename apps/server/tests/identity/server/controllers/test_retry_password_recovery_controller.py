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


class _FixedTokenProvider:
    def __init__(self, token: str) -> None:
        self._token = token

    def generate(self) -> str:
        return self._token

    @staticmethod
    def hash(token: str) -> str:
        return sha256(token.encode('utf-8')).hexdigest()


class _FixedClockProvider:
    def __init__(self, current: datetime) -> None:
        self._current = current

    def now(self) -> datetime:
        return self._current


class TestRetryPasswordRecoveryController:
    def test_retry_requires_bff_protection_and_valid_context(
        self,
        client: TestClient,
    ) -> None:
        unauthorized = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/password-recoveries/retry',
                headers={'x-shifu-bff-secret': ''},
                json={'recovery_handle': 'opaque-handle'},
            ),
        )
        invalid = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/password-recoveries/retry',
                json={'recovery_handle': ''},
            ),
        )

        assert unauthorized.status_code == 401
        assert invalid.status_code == 422
        assert invalid.json()['code'] == 'validation_error'

    def test_terminal_delivery_issue_replaces_the_persisted_recovery_token(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        handle = 'retry-handle'
        old_token = 'old-recovery-token'
        replacement_token = 'replacement-recovery-token'
        database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            account = AccountFaker.fake(
                email='retry@example.com',
                created_at=now,
                updated_at=now,
            )
            repositories.accounts.add(account)
            repositories.account_action_tokens.add(
                AccountActionToken(
                    id='00000000000000000000000005',
                    account_id=account.id,
                    type=AccountActionTokenType.PASSWORD_RECOVERY,
                    status=AccountActionTokenStatus.PENDING,
                    token_hash=_FixedTokenProvider.hash(old_token),
                    issued_at=now - timedelta(minutes=2),
                    expires_at=now + timedelta(hours=1),
                    updated_at=now,
                    communication_id='00000000000000000000000006',
                    pending_handle_hash=_FixedTokenProvider.hash(handle),
                    delivery_status=AccountActionTokenDeliveryStatus.PERMANENT_FAILURE,
                )
            )

        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_action_token_provider] = lambda: (
            _FixedTokenProvider(replacement_token)
        )
        app.dependency_overrides[IdentityPipe.get_recovery_handle_provider] = lambda: (
            _FixedTokenProvider(handle)
        )
        app.dependency_overrides[IdentityPipe.get_clock_provider] = lambda: (
            _FixedClockProvider(now)
        )
        with TestClient(
            app,
            headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
        ) as client:
            response = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/password-recoveries/retry',
                    json={'recovery_handle': handle},
                ),
            )

        assert response.status_code == 202
        assert response.json() == {'recovery_handle': handle, 'is_decoy': False}
        with database.transaction() as repositories:
            tokens = (
                repositories.account_action_tokens.find_many_by_account_id_and_type(
                    account.id,
                    AccountActionTokenType.PASSWORD_RECOVERY,
                )
            )
            assert len(tokens) == 2
            assert tokens[0].status is AccountActionTokenStatus.INVALIDATED
            assert tokens[1].status is AccountActionTokenStatus.PENDING
            assert tokens[1].token_hash == _FixedTokenProvider.hash(replacement_token)

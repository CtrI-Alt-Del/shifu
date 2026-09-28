from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.identity.core.domain.enums import AccountActionTokenType
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.pipes import IdentityPipe
from shifu.shared.constants import ENVIRONMENT

if TYPE_CHECKING:
    from httpx import Response

    from tests.fixtures.postgres_fixture import PostgresDatabase


class _SequenceTokenProvider:
    def __init__(self, *tokens: str) -> None:
        self._tokens = list(tokens)

    def generate(self) -> str:
        return self._tokens.pop(0)

    @staticmethod
    def hash(token: str) -> str:
        return sha256(token.encode('utf-8')).hexdigest()


class _FixedClockProvider:
    def __init__(self, current: datetime) -> None:
        self._current = current

    def now(self) -> datetime:
        return self._current


class TestRequestPasswordRecoveryController:
    def test_request_requires_bff_protection(self, client: TestClient) -> None:
        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/password-recovery-requests',
                headers={'x-shifu-bff-secret': ''},
                json={'email': 'learner@example.com'},
            ),
        )

        assert response.status_code == 401

    def test_invalid_request_returns_safe_validation_without_persistence(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/identity/password-recovery-requests',
                json={'email': 'not-an-email'},
            ),
        )

        assert response.status_code == 422
        assert response.json()['code'] == 'validation_error'
        database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            assert (
                repositories.accounts.find_non_deleted_by_email('not-an-email') is None
            )

    def test_request_distinguishes_bff_decoy_from_real_persistence(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        action_token = 'recovery-token'
        recovery_handle = 'recovery-handle'
        action_token_provider = _SequenceTokenProvider(
            'confirmation-token',
            action_token,
        )
        recovery_handle_provider = _SequenceTokenProvider(
            recovery_handle,
            'decoy-recovery-handle',
        )
        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[IdentityPipe.get_action_token_provider] = lambda: (
            action_token_provider
        )
        app.dependency_overrides[IdentityPipe.get_recovery_handle_provider] = lambda: (
            recovery_handle_provider
        )
        app.dependency_overrides[IdentityPipe.get_clock_provider] = lambda: (
            _FixedClockProvider(now)
        )

        with TestClient(
            app,
            headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
        ) as client:
            registration = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/registrations',
                    json={
                        'display_name': 'Grace Hopper',
                        'email': 'grace@example.com',
                        'password': 'correct horse battery staple',
                    },
                ),
            )
            real = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/password-recovery-requests',
                    json={'email': ' GRACE@example.com '},
                ),
            )
            decoy = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    '/identity/password-recovery-requests',
                    json={'email': 'missing@example.com'},
                ),
            )

        assert registration.status_code == 202
        assert real.status_code == decoy.status_code == 202
        assert set(real.json()) == set(decoy.json()) == {'recovery_handle', 'is_decoy'}
        assert real.json() == {'recovery_handle': recovery_handle, 'is_decoy': False}
        assert decoy.json()['is_decoy'] is True

        database = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            account = repositories.accounts.find_non_deleted_by_email(
                'grace@example.com'
            )
            assert account is not None
            tokens = (
                repositories.account_action_tokens.find_many_by_account_id_and_type(
                    account.id,
                    AccountActionTokenType.PASSWORD_RECOVERY,
                )
            )
            assert len(tokens) == 1
            assert tokens[0].token_hash == _SequenceTokenProvider.hash(action_token)
            assert tokens[0].token_hash != action_token
            assert tokens[0].expires_at == now + timedelta(hours=1)
            assert (
                repositories.accounts.find_non_deleted_by_email('missing@example.com')
                is None
            )

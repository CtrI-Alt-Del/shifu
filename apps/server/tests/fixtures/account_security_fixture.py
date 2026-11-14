"""Real signing/JWKS and application setup for account boundary tests."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import Engine
from fastapi import FastAPI
from fastapi.testclient import TestClient
import jwt
from jwt.algorithms import OKPAlgorithm
import pytest

import shifu.app as app_module
from shifu.app import FastAPIApp
from shifu.fakers.identity.entities import AccountFaker
from shifu.identity.core.domain.entities import Account
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.identity.providers.auth.password_hashing.argon2id_hash_provider import (
    Argon2idHashProvider,
)
from shifu.shared.constants import ENVIRONMENT
from tests.fixtures.postgres_fixture import PostgresDatabase


@dataclass(frozen=True)
class AccountSecurityFixture:
    app: FastAPI
    engine: Engine
    client: TestClient
    database: SqlalchemyIdentityDatabase
    account: Account
    key: Ed25519PrivateKey

    def token(
        self,
        *,
        session: str = 'session-a',
        version: int | None = None,
        account_id: str | None = None,
        claims: dict[str, object] | None = None,
        **overrides: object,
    ) -> str:
        now = datetime.now(UTC)
        payload: dict[str, object] = {
            'iss': ENVIRONMENT.auth_issuer,
            'aud': ENVIRONMENT.auth_audience,
            'sub': account_id or self.account.id,
            'iat': now,
            'exp': now + timedelta(minutes=5),
            'jti': str(uuid4()),
            'sid': session,
            'access_version': self.account.access_version
            if version is None
            else version,
        }
        payload.update(claims or {})
        payload.update(overrides)
        return jwt.encode(
            payload, self.key, algorithm='EdDSA', headers={'kid': 'account-test'}
        )

    def headers(
        self,
        *,
        session: str = 'session-a',
        version: int | None = None,
        account_id: str | None = None,
        claims: dict[str, object] | None = None,
        **overrides: object,
    ) -> dict[str, str]:
        return {
            'Authorization': 'Bearer '
            + self.token(
                session=session,
                version=version,
                account_id=account_id,
                claims=claims,
                **overrides,
            )
        }


@pytest.fixture
def account_security(
    postgres_database: PostgresDatabase, monkeypatch: pytest.MonkeyPatch
) -> Iterator[AccountSecurityFixture]:
    key = Ed25519PrivateKey.generate()
    public = json.loads(OKPAlgorithm.to_jwk(key.public_key()))
    public['kid'] = 'account-test'
    document = json.dumps({'keys': [public]}).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(document)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    app: FastAPI | None = None
    try:
        monkeypatch.setattr(
            app_module,
            'ENVIRONMENT',
            ENVIRONMENT.model_copy(
                update={
                    'auth_jwks_url': f'http://127.0.0.1:{server.server_port}/jwks',
                }
            ),
        )
        database = SqlalchemyIdentityDatabase(postgres_database.engine)
        account = AccountFaker.fake(
            access_version=4,
            password_hash=Argon2idHashProvider().hash('current-password'),
        )
        with database.transaction() as repositories:
            repositories.accounts.add(account)
        app = FastAPIApp.register(postgres_database.engine)
        with TestClient(
            app,
            raise_server_exceptions=False,
            headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret},
        ) as client:
            yield AccountSecurityFixture(
                app=app,
                engine=postgres_database.engine,
                client=client,
                database=database,
                account=account,
                key=key,
            )
    finally:
        if app is not None:
            app.dependency_overrides.clear()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

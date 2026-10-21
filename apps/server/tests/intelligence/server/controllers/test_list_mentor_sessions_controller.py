import base64
import hashlib
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from shifu.intelligence.core.domain.entities import MentorSession
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.intelligence.server.controllers.conftest import MENTOR_ACCOUNT
from tests.fixtures.postgres_fixture import PostgresDatabase

if TYPE_CHECKING:
    from httpx import Response


def _encode_cursor(payload: object) -> str:
    serialized = json.dumps(payload, separators=(',', ':')).encode()
    return base64.urlsafe_b64encode(serialized).decode().rstrip('=')


class TestListMentorSessionsController:
    def test_should_search_titles_and_advance_account_scoped_pages(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        identifier_provider = SystemIdentifierProvider()
        timestamp = datetime.now(UTC)
        with database.transaction() as repositories:
            for _ in range(31):
                session = MentorSession(
                    id=identifier_provider.generate(),
                    account_id=MENTOR_ACCOUNT.account_id,
                    title='Conversa de teste',
                    created_at=timestamp,
                    updated_at=timestamp,
                    last_activity_at=timestamp,
                )
                repositories.mentor_sessions.add(
                    session,
                    str(uuid4()),
                    hashlib.sha256(session.id.encode()).hexdigest(),
                )

        first_page = cast(
            'Response',
            mentor_client.get('/intelligence/mentor-sessions?search=CONVERSA'),
        )
        assert first_page.status_code == 200
        assert first_page.headers['cache-control'] == 'private, no-store'
        assert len(first_page.json()['items']) == 30
        assert first_page.json()['next_cursor'] is not None

        next_page = cast(
            'Response',
            mentor_client.get(
                '/intelligence/mentor-sessions',
                params={
                    'search': 'conversa',
                    'cursor': first_page.json()['next_cursor'],
                },
            ),
        )
        assert next_page.status_code == 200
        assert len(next_page.json()['items']) == 1
        assert next_page.json()['next_cursor'] is None

        mismatch = cast(
            'Response',
            mentor_client.get(
                '/intelligence/mentor-sessions',
                params={
                    'search': 'outra busca',
                    'cursor': first_page.json()['next_cursor'],
                },
            ),
        )
        assert mismatch.status_code == 422

    def test_should_reject_malformed_cursor_as_validation_error(
        self, mentor_client: TestClient
    ) -> None:
        response = cast(
            'Response',
            mentor_client.get('/intelligence/mentor-sessions?cursor=not-a-cursor'),
        )

        assert response.status_code == 422
        assert response.headers['cache-control'] == 'private, no-store'

    @pytest.mark.parametrize(
        'cursor',
        [
            '',
            'x' * 2049,
            _encode_cursor([]),
            _encode_cursor({'kind': 'sessions'}),
            _encode_cursor(
                {
                    'kind': 'sessions',
                    'account_id': MENTOR_ACCOUNT.account_id,
                    'search': None,
                    'activity_at': None,
                    'id': '01JSESSION000000000000000000',
                }
            ),
            _encode_cursor(
                {
                    'kind': 'sessions',
                    'account_id': MENTOR_ACCOUNT.account_id,
                    'search': None,
                    'activity_at': 'not-a-timestamp',
                    'id': '01JSESSION000000000000000000',
                }
            ),
        ],
    )
    def test_should_reject_invalid_cursor_shapes_and_timestamps(
        self, mentor_client: TestClient, cursor: str
    ) -> None:
        response = cast(
            'Response',
            mentor_client.get(
                '/intelligence/mentor-sessions', params={'cursor': cursor}
            ),
        )

        assert response.status_code == 422
        assert response.headers['cache-control'] == 'private, no-store'

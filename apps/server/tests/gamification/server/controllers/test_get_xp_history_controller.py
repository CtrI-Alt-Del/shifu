from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.core.domain.entities import XpGrant
from shifu.gamification.core.domain.enums import XpSource
from shifu.gamification.core.domain.structures import XpOrigin
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

ACCOUNT_ID = '01SHF00000000000000ACCOUNT'
OTHER_ACCOUNT_ID = '01SHF00000000000000OTHERA'
TIME_ZONE = 'America/Sao_Paulo'
NOW = datetime(2026, 1, 1, tzinfo=UTC)
NEWEST = datetime(2026, 1, 20, 10, 0, tzinfo=UTC)
TIED = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
OLDEST = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)
OCCURRED_EARLIER = datetime(2026, 1, 18, 10, 0, tzinfo=UTC)

_SEEDED_TOTAL = 60 + 50 + 25 + 100


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token == 'other-access-token':
            return AuthenticatedUser(
                account_id=OTHER_ACCOUNT_ID,
                display_name='Outra Pessoa',
                time_zone=TIME_ZONE,
            )
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone=TIME_ZONE,
        )


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _TestAuthenticationProvider()
    application.state.gamification_database = SqlalchemyGamificationDatabase(
        postgres_database.engine
    )
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


def _grant(
    *,
    account_id: str,
    identifier: str,
    amount: int,
    source: XpSource,
    reference_id: str,
    label: str,
    granted_at: datetime,
    occurred_at: datetime | None = None,
) -> XpGrant:
    return XpGrant.create(
        id=identifier,
        account_id=account_id,
        # Identifier columns are `varchar(26)`; keep the derived fact id the
        # same width rather than prefixing it.
        fact_id=identifier.replace('GRANT', 'FACTX'),
        amount=amount,
        origin=XpOrigin(source=source, reference_id=reference_id, label=label),
        occurred_at=occurred_at if occurred_at is not None else granted_at,
        granted_at=granted_at,
    )


class TestGetXpHistoryController:
    @staticmethod
    def _seed(postgres_database: PostgresDatabase) -> None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=ACCOUNT_ID,
                    total_xp=_SEEDED_TOTAL,
                    created_at=NOW,
                    updated_at=NOW,
                )
            )
            repositories.xp_grants.add(
                _grant(
                    account_id=ACCOUNT_ID,
                    identifier='01SHF000000000000000GRANTA',
                    amount=60,
                    source=XpSource.DIAGNOSIS,
                    reference_id='skill-1',
                    label='Lógica de programação',
                    granted_at=NEWEST,
                    occurred_at=OCCURRED_EARLIER,
                )
            )
            # Two grants sharing a single `granted_at`, as one achievement
            # cascade produces: the `id` tiebreak must totally order them.
            repositories.xp_grants.add(
                _grant(
                    account_id=ACCOUNT_ID,
                    identifier='01SHF000000000000000GRANTB',
                    amount=50,
                    source=XpSource.COMPETENCY_MASTERY,
                    reference_id='competency-1',
                    label='Condicionais',
                    granted_at=TIED,
                )
            )
            repositories.xp_grants.add(
                _grant(
                    account_id=ACCOUNT_ID,
                    identifier='01SHF000000000000000GRANTC',
                    amount=25,
                    source=XpSource.ACHIEVEMENT,
                    reference_id='primeiro-passo',
                    label='Primeiro Passo',
                    granted_at=TIED,
                )
            )
            repositories.xp_grants.add(
                _grant(
                    account_id=ACCOUNT_ID,
                    identifier='01SHF000000000000000GRANTD',
                    amount=100,
                    source=XpSource.SKILL_COMPLETION,
                    reference_id='skill-2',
                    label='Estruturas de dados',
                    granted_at=OLDEST,
                )
            )

    def test_should_return_every_record_newest_concession_first(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database)

        response = client.get(
            '/gamification/xp-history',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert response.status_code == 200
        body = response.json()
        assert [entry['id'] for entry in body['entries']] == [
            '01SHF000000000000000GRANTA',
            '01SHF000000000000000GRANTC',
            '01SHF000000000000000GRANTB',
            '01SHF000000000000000GRANTD',
        ]
        assert [entry['title'] for entry in body['entries']] == [
            'Lógica de programação',
            'Primeiro Passo',
            'Condicionais',
            'Estruturas de dados',
        ]

    def test_should_report_a_total_equal_to_the_returned_amounts_and_the_profile(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database)

        response = client.get(
            '/gamification/xp-history',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        body = response.json()
        assert body['totalXp'] == sum(entry['amount'] for entry in body['entries'])
        assert body['totalXp'] == _SEEDED_TOTAL

    def test_should_serialize_the_descriptor_source_and_both_dates(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        """The repository read and its SQL ordering have no test of their own
        by rule; this round trip through real migrations is their proof."""
        self._seed(postgres_database)

        response = client.get(
            '/gamification/xp-history',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        entries = {entry['id']: entry for entry in response.json()['entries']}
        diagnostic = entries['01SHF000000000000000GRANTA']
        assert diagnostic['source'] == 'diagnosis'
        assert diagnostic['detail'] == 'Diagnóstico concluído'
        assert diagnostic['grantedAt'].startswith('2026-01-20')
        assert diagnostic['occurredAt'].startswith('2026-01-18')
        assert entries['01SHF000000000000000GRANTB']['detail'] == (
            'Primeiro domínio de Competência'
        )
        assert entries['01SHF000000000000000GRANTD']['detail'] == 'Habilidade concluída'

    def test_should_return_an_empty_history_for_a_profile_without_grants(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=ACCOUNT_ID, total_xp=0, created_at=NOW, updated_at=NOW
                )
            )

        response = client.get(
            '/gamification/xp-history',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert response.status_code == 200
        assert response.json() == {'totalXp': 0, 'entries': []}

    def test_should_not_leak_another_accounts_records(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database)
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=OTHER_ACCOUNT_ID,
                    total_xp=10,
                    created_at=NOW,
                    updated_at=NOW,
                )
            )
            repositories.xp_grants.add(
                _grant(
                    account_id=OTHER_ACCOUNT_ID,
                    identifier='01SHF000000000000000GRANTE',
                    amount=10,
                    source=XpSource.DIAGNOSIS,
                    reference_id='skill-9',
                    label='Outra Habilidade',
                    granted_at=NEWEST,
                )
            )

        response = client.get(
            '/gamification/xp-history',
            headers={'Authorization': 'Bearer other-access-token'},
        )

        assert response.status_code == 200
        body = response.json()
        assert [entry['title'] for entry in body['entries']] == ['Outra Habilidade']
        assert body['totalXp'] == 10

    def test_should_return_not_found_without_a_gamification_profile(
        self, client: TestClient
    ) -> None:
        response = client.get(
            '/gamification/xp-history',
            headers={'Authorization': 'Bearer test-access-token'},
        )

        assert response.status_code == 404

    def test_should_reject_an_unauthenticated_request(self, client: TestClient) -> None:
        response = client.get('/gamification/xp-history')

        assert response.status_code == 401

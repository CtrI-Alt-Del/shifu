import threading
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, date, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from shifu.app import FastAPIApp
from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.fakers.identity.entities import AccountFaker
from shifu.gamification.core.domain.entities import GamificationProfile
from shifu.gamification.core.domain.structures import PracticeStreak
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
    GamificationProfilesRepository,
)
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.pipes import SharedPipe
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

ACCOUNT_ID = '01SHF00000000000000ACCOUNT'
OTHER_ACCOUNT_ID = '01SHF00000000000000OTHERA'
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 9, 15, 18, 50, tzinfo=UTC)
STREAK = PracticeStreak(current=2, longest=4, latest_practice_date=date(2026, 9, 14))
OWNER = {'Authorization': 'Bearer test-access-token'}
OTHER = {'Authorization': 'Bearer other-access-token'}
SETTINGS_URL = '/gamification/streak-reminder'
HOUR_URL = '/gamification/streak-reminder/hour'
ANSWER_URL = '/gamification/streak-reminder/invite-answer'
_TIMEOUT_SECONDS = 20.0
_LOCK_WAIT_SECONDS = 5.0


class _FixedClockProvider(ClockProvider):
    def now(self) -> datetime:
        return NOW


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        accounts = {
            'test-access-token': ACCOUNT_ID,
            'other-access-token': OTHER_ACCOUNT_ID,
        }
        account_id = accounts.get(access_token)
        if account_id is None:
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=account_id,
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
            session_id='test-session',
            token_access_version=1,
            account_access_version=1,
        )


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    application = FastAPIApp.register(postgres_database.engine)
    identity_database = SqlalchemyIdentityDatabase(postgres_database.engine)
    with identity_database.transaction() as repositories:
        repositories.accounts.add(
            AccountFaker.fake(
                id=ACCOUNT_ID,
                email='streak-hour@example.test',
                access_version=1,
            )
        )
        repositories.accounts.add(
            AccountFaker.fake(
                id=OTHER_ACCOUNT_ID,
                email='other-streak-hour@example.test',
                access_version=1,
            )
        )
    application.state.authentication_provider = _TestAuthenticationProvider()
    application.state.gamification_database = SqlalchemyGamificationDatabase(
        postgres_database.engine
    )
    application.dependency_overrides[SharedPipe.get_clock_provider] = lambda: (
        _FixedClockProvider()
    )
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestChangeStreakReminderHourController:
    @staticmethod
    def _seed(
        postgres_database: PostgresDatabase,
        account_id: str,
        *,
        reminder_hour: int = 18,
    ) -> None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=account_id,
                    total_xp=120,
                    streak=STREAK,
                    reminder_hour=reminder_hour,
                    created_at=CREATED_AT,
                )
            )

    @staticmethod
    def _stored_hour(client: TestClient, headers: dict[str, str]) -> int:
        response = client.get(SETTINGS_URL, headers=headers)
        assert response.status_code == 200
        return response.json()['hour']

    @pytest.mark.parametrize('hour', [6, 7, 19, 21, 22])
    def test_should_persist_every_accepted_hour_for_a_fresh_read(
        self, client: TestClient, postgres_database: PostgresDatabase, hour: int
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID)

        response = client.put(HOUR_URL, json={'hour': hour}, headers=OWNER)

        assert response.status_code == 200
        assert response.json() == {'hour': hour, 'inviteStatus': 'pending'}
        assert client.get(SETTINGS_URL, headers=OWNER).json() == {
            'hour': hour,
            'inviteStatus': 'pending',
        }

    @pytest.mark.parametrize('hour', [5, 23, 0, 24, -1, 100])
    def test_should_reject_an_hour_outside_6_to_22_and_keep_the_stored_hour(
        self, client: TestClient, postgres_database: PostgresDatabase, hour: int
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID, reminder_hour=20)

        response = client.put(HOUR_URL, json={'hour': hour}, headers=OWNER)

        assert response.status_code == 422
        assert self._stored_hour(client, OWNER) == 20

    @pytest.mark.parametrize(
        'body',
        [
            {'hour': '18'},
            {'hour': 18.5},
            {'hour': True},
            {'hour': None},
            {},
            {'hour': 18, 'minute': 30},
        ],
    )
    def test_should_reject_a_body_that_is_not_a_single_whole_integer_hour(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
        body: dict[str, object],
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID, reminder_hour=20)

        response = client.put(HOUR_URL, json=body, headers=OWNER)

        assert response.status_code == 422
        assert self._stored_hour(client, OWNER) == 20

    def test_should_change_only_the_reminder_hour(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID)

        client.put(HOUR_URL, json={'hour': 9}, headers=OWNER)

        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            profile = repositories.profiles.find_by_account_id(ACCOUNT_ID)
        assert profile is not None
        assert profile.reminder_hour == 9
        assert profile.total_xp == 120
        assert profile.streak == STREAK
        assert profile.reminder_invite_answered_at is None
        assert profile.updated_at == NOW

    def test_should_not_change_another_accounts_hour(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID, reminder_hour=18)
        self._seed(postgres_database, OTHER_ACCOUNT_ID, reminder_hour=21)

        client.put(HOUR_URL, json={'hour': 7}, headers=OWNER)

        assert self._stored_hour(client, OWNER) == 7
        assert self._stored_hour(client, OTHER) == 21

    def test_should_answer_not_found_when_the_account_has_no_profile(
        self, client: TestClient
    ) -> None:
        response = client.put(HOUR_URL, json={'hour': 9}, headers=OWNER)

        assert response.status_code == 404

    def test_should_reject_a_request_without_a_session_and_change_nothing(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        self._seed(postgres_database, ACCOUNT_ID, reminder_hour=20)

        response = client.put(HOUR_URL, json={'hour': 9})

        assert response.status_code == 401
        assert self._stored_hour(client, OWNER) == 20


class _PausingProfilesRepository:
    """Delegates to the real repository and pauses the first locking load.

    The pause holds the first request between its read and its write, which is
    the window where a concurrent read-modify-write used to be lost.
    """

    def __init__(
        self,
        inner: GamificationProfilesRepository,
        on_first_load: Callable[[], None],
        is_first_load: Callable[[], bool],
    ) -> None:
        self._inner = inner
        self._on_first_load = on_first_load
        self._is_first_load = is_first_load

    def find_by_account_id(self, account_id: str) -> GamificationProfile | None:
        return self._inner.find_by_account_id(account_id)

    def find_by_account_id_for_update(
        self, account_id: str
    ) -> GamificationProfile | None:
        profile = self._inner.find_by_account_id_for_update(account_id)
        if self._is_first_load():
            self._on_first_load()
        return profile

    def find_many_reminder_candidates(
        self, *, practiced_since: date, after_account_id: str | None, limit: int
    ) -> tuple[GamificationProfile, ...]:
        return self._inner.find_many_reminder_candidates(
            practiced_since=practiced_since,
            after_account_id=after_account_id,
            limit=limit,
        )

    def add(self, profile: GamificationProfile) -> None:
        self._inner.add(profile)

    def update(self, profile: GamificationProfile) -> None:
        self._inner.update(profile)

    def remove(self, profile: GamificationProfile) -> None:
        self._inner.remove(profile)


class _PausingGamificationDatabase:
    """Composition seam: the real database with a pausing profiles repository."""

    def __init__(
        self,
        inner: GamificationDatabase,
        on_first_load: Callable[[], None],
    ) -> None:
        self._inner = inner
        self._on_first_load = on_first_load
        self._lock = threading.Lock()
        self._loads = 0

    def _is_first_load(self) -> bool:
        with self._lock:
            self._loads += 1
            return self._loads == 1

    @contextmanager
    def transaction(self) -> Generator[GamificationDatabaseRepositories]:
        with self._inner.transaction() as repositories:
            yield replace(
                repositories,
                profiles=_PausingProfilesRepository(
                    repositories.profiles, self._on_first_load, self._is_first_load
                ),
            )


def _waiting_on_a_lock(engine: Engine) -> bool:
    with engine.connect() as connection:
        waiting = connection.execute(
            text(
                'SELECT count(*) FROM pg_stat_activity '
                "WHERE datname = current_database() AND wait_event_type = 'Lock'"
            )
        ).scalar_one()
    return waiting > 0


class TestConcurrentStreakReminderRequests:
    """Two overlapping read-modify-write requests on one profile both survive.

    The first request is held after it loaded the profile, until the second
    request is blocked on the row lock. Only then does the first one write.
    Without the lock the second request would not block, would commit while
    the first is still paused, and the first would then overwrite it with the
    stale profile it loaded.
    """

    @staticmethod
    def _seed(postgres_database: PostgresDatabase) -> None:
        database = SqlalchemyGamificationDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            repositories.profiles.add(
                GamificationProfileFaker.fake(
                    account_id=ACCOUNT_ID,
                    streak=STREAK,
                    reminder_hour=18,
                    created_at=CREATED_AT,
                )
            )

    @staticmethod
    def _overlap(
        application: FastAPI,
        client: TestClient,
        engine: Engine,
        first: Callable[[TestClient], int],
        second: Callable[[TestClient], int],
    ) -> tuple[int, int]:
        first_loaded = threading.Event()
        release_first = threading.Event()

        def hold_first_request() -> None:
            first_loaded.set()
            # Release when the second request waits on the row lock. When the
            # lock is missing the second request never waits, so the pause
            # times out after the second one has already committed.
            deadline = threading.Timer(_LOCK_WAIT_SECONDS, release_first.set)
            deadline.start()
            try:
                while not release_first.is_set():
                    if _waiting_on_a_lock(engine):
                        return
                    release_first.wait(0.05)
            finally:
                deadline.cancel()

        application.state.gamification_database = _PausingGamificationDatabase(
            application.state.gamification_database, hold_first_request
        )
        statuses: list[int] = [0, 0]

        def run(index: int, action: Callable[[TestClient], int]) -> None:
            # One client shares one event loop, so both requests reach the
            # same rate-limit connection and run their sync handlers in
            # separate worker threads.
            statuses[index] = action(client)

        first_thread = threading.Thread(target=run, args=(0, first))
        first_thread.start()
        assert first_loaded.wait(_TIMEOUT_SECONDS)
        second_thread = threading.Thread(target=run, args=(1, second))
        second_thread.start()
        for thread in (first_thread, second_thread):
            thread.join(_TIMEOUT_SECONDS * 2)
            assert not thread.is_alive()
        return statuses[0], statuses[1]

    @staticmethod
    def _change_hour(client: TestClient) -> int:
        return client.put(HOUR_URL, json={'hour': 7}, headers=OWNER).status_code

    @staticmethod
    def _answer_invite(client: TestClient) -> int:
        return client.post(ANSWER_URL, headers=OWNER).status_code

    def test_should_keep_the_hour_and_the_invite_answer_when_the_hour_request_starts_first(
        self,
        application: FastAPI,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        self._seed(postgres_database)

        statuses = self._overlap(
            application,
            client,
            postgres_database.engine,
            self._change_hour,
            self._answer_invite,
        )

        assert statuses == (200, 200)
        assert client.get(SETTINGS_URL, headers=OWNER).json() == {
            'hour': 7,
            'inviteStatus': 'answered',
        }

    def test_should_keep_the_hour_and_the_invite_answer_when_the_answer_request_starts_first(
        self,
        application: FastAPI,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        self._seed(postgres_database)

        statuses = self._overlap(
            application,
            client,
            postgres_database.engine,
            self._answer_invite,
            self._change_hour,
        )

        assert statuses == (200, 200)
        assert client.get(SETTINGS_URL, headers=OWNER).json() == {
            'hour': 7,
            'inviteStatus': 'answered',
        }

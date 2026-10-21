from typing import TYPE_CHECKING, cast
import pytest
from fastapi.testclient import TestClient
from shifu.fakers.identity.entities.account_faker import AccountFaker
from shifu.identity.database.sqlalchemy.identity_database import (
    SqlalchemyIdentityDatabase,
)
from shifu.identity.providers.identity_mentor_access_provider import (
    IdentityMentorAccessProvider,
)
from shifu.intelligence.pipes import IntelligencePipe

if TYPE_CHECKING:
    from fastapi import FastAPI

from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.conftest import MENTOR_ACCOUNT
from tests.intelligence.server.controllers.mentor_response_scenarios import (
    create_session,
    complete_response,
)


class TestCancelMentorResponseController:
    def test_should_cancel_and_replay_preserving_learner(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session, attempt, learner = create_session(mentor_client)
        url = f'/intelligence/mentor-sessions/{session}/responses/{attempt}/cancel'
        payload = {'submission_key': '223e4567-e89b-42d3-a456-426614174000'}
        first = mentor_client.post(url, json=payload)
        replay = mentor_client.post(url, json=payload)
        assert first.status_code == replay.status_code == 200
        assert first.json()['status'] == 'cancelled'
        assert first.json()['blocks'] == []
        assert first.headers['cache-control'] == 'private, no-store'
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            message = repositories.mentor_messages.find_by_id(
                MENTOR_ACCOUNT.account_id, session, learner
            )
            assert message is not None
            assert message.content == 'Pergunta inicial'
            assert (
                repositories.mentor_messages.find_response(
                    MENTOR_ACCOUNT.account_id, session, learner
                )
                is None
            )

    def test_should_not_cancel_completed_response(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session, attempt, learner = create_session(mentor_client)
        complete_response(postgres_database, session, attempt, learner)
        result = mentor_client.post(
            f'/intelligence/mentor-sessions/{session}/responses/{attempt}/cancel',
            json={'submission_key': '223e4567-e89b-42d3-a456-426614174000'},
        )
        assert result.status_code == 409

    @pytest.mark.parametrize(
        ('access_version', 'expected_status'), [(1, 200), (2, 403)]
    )
    def test_should_cancel_with_current_identity_and_reject_stale_revision(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
        access_version: int,
        expected_status: int,
    ) -> None:
        app = cast('FastAPI', mentor_client.app)
        identity = SqlalchemyIdentityDatabase(postgres_database.engine)
        account = AccountFaker.fake(id=MENTOR_ACCOUNT.account_id, access_version=1)
        with identity.transaction() as repositories:
            repositories.accounts.add(account)
        actual_access = IdentityMentorAccessProvider(identity)
        app.dependency_overrides[IntelligencePipe.get_mentor_access_provider] = lambda: (
            actual_access
        )
        session, attempt, learner = create_session(mentor_client)
        if access_version == 2:
            account.invalidate_other_accesses(account.updated_at)
            with identity.transaction() as repositories:
                repositories.accounts.update(account)
        response = mentor_client.post(
            f'/intelligence/mentor-sessions/{session}/responses/{attempt}/cancel',
            json={'submission_key': '223e4567-e89b-42d3-a456-426614174000'},
        )
        assert response.status_code == expected_status
        assert response.headers['cache-control'] == 'private, no-store'
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            current = repositories.mentor_response_attempts.find_current(
                MENTOR_ACCOUNT.account_id, session
            )
            assert current is not None
            assert current.id == attempt
            assert current.status.value == (
                'cancelled' if expected_status == 200 else 'queued'
            )
            assert current.learner_message_id == learner
            cancellation = repositories.mentor_response_attempts.find_submission(
                MENTOR_ACCOUNT.account_id,
                session,
                '223e4567-e89b-42d3-a456-426614174000',
            )
            if expected_status == 200:
                assert cancellation is not None
                assert cancellation[0].id == attempt
                assert cancellation[0].status.value == 'cancelled'
                assert cancellation[1] == 'cancel:' + attempt
                assert response.json()['status'] == 'cancelled'
            else:
                assert cancellation is None

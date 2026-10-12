from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from shifu.app import FastAPIApp
from shifu.fakers.identity.entities.account_faker import AccountFaker
from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.database.sqlalchemy.identity_database import (
    SqlalchemyIdentityDatabase,
)
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.database.sqlalchemy.models import EventModel
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe
from shifu.shared.settings import get_settings
from tests.intelligence.server.controllers.conftest import (
    MENTOR_ACCOUNT,
    MentorTitleWorkflowStub,
    configure_mentor_access,
)

if TYPE_CHECKING:
    from tests.fixtures.postgres_fixture import PostgresDatabase


class TestMentorRuntimeCompositionController:
    @pytest.mark.parametrize('configured', [False, True])
    def test_default_runtime_refuses_startup_when_redis_is_unavailable(
        self,
        postgres_database: 'PostgresDatabase',
        monkeypatch: pytest.MonkeyPatch,
        configured: bool,
    ) -> None:
        settings = get_settings().model_copy(
            update={
                'redis_url': 'redis://127.0.0.1:1/0',
                'openrouter_api_key': 'disposable-unused-key' if configured else None,
                'openrouter_prompt_logging_disabled': configured,
                'mentor_telemetry_enabled': False,
            }
        )
        monkeypatch.setattr('shifu.app.get_settings', lambda: settings)
        app = FastAPIApp.register(postgres_database.engine)
        with (
            pytest.raises(ServiceUnavailableError, match='Redis está indisponível'),
            TestClient(app),
        ):
            pytest.fail('Application must not accept requests after startup failure')

    @pytest.mark.parametrize(
        ('status', 'exists', 'expected'),
        [
            (AccountStatus.ACTIVE, True, 404),
            (AccountStatus.PENDING_CONFIRMATION, True, 403),
            (AccountStatus.DELETED, True, 403),
            (AccountStatus.ACTIVE, False, 403),
        ],
    )
    def test_default_history_access_requires_an_existing_active_account(
        self,
        postgres_database: 'PostgresDatabase',
        status: AccountStatus,
        exists: bool,
        expected: int,
    ) -> None:
        account = AccountFaker.fake(status=status)
        identity = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        if exists:
            with identity.transaction() as repositories:
                repositories.accounts.add(account)
        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            AuthenticatedUser(
                account_id=account.id,
                display_name=account.display_name,
                time_zone=None,
            )
        )
        with TestClient(app, headers={'Authorization': 'Bearer synthetic'}) as http:
            response = http.get(
                '/intelligence/mentor-sessions/00000000000000000000000000'
            )
        assert response.status_code == expected
        assert response.headers['cache-control'] == 'private, no-store'

    @pytest.mark.parametrize(
        ('status', 'exists', 'expected'),
        [
            (AccountStatus.ACTIVE, True, 201),
            (AccountStatus.PENDING_CONFIRMATION, True, 403),
            (AccountStatus.DELETED, True, 403),
            (AccountStatus.ACTIVE, False, 403),
        ],
    )
    def test_default_access_accepts_only_existing_active_accounts(
        self,
        postgres_database: 'PostgresDatabase',
        status: AccountStatus,
        exists: bool,
        expected: int,
    ) -> None:
        account = AccountFaker.fake(status=status)
        identity = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        if exists:
            with identity.transaction() as repositories:
                repositories.accounts.add(account)
        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            AuthenticatedUser(
                account_id=account.id,
                display_name=account.display_name,
                time_zone=None,
            )
        )
        app.dependency_overrides[
            IntelligencePipe.get_generate_mentor_title_workflow
        ] = MentorTitleWorkflowStub
        with TestClient(app, headers={'Authorization': 'Bearer synthetic'}) as http:
            response = http.post(
                '/intelligence/mentor-sessions',
                json={
                    'submission_key': '86238f77-0723-4470-a318-d59003553b62',
                    'first_message': 'Quero entender variáveis.',
                },
            )
        assert response.status_code == expected
        assert response.headers['cache-control'] == 'private, no-store'
        intelligence = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        with intelligence.transaction() as repositories:
            sessions = repositories.mentor_sessions.find_many(account.id, None, None)
            if expected == 201:
                body = response.json()
                assert len(sessions.items) == 1
                assert sessions.items[0].id == body['session']['id']
                assert body['response']['status'] == 'queued'
                attempt = repositories.mentor_response_attempts.find_current(
                    account.id, body['session']['id']
                )
                assert attempt is not None
                assert attempt.access_revision == str(account.access_version)
                assert attempt.operation_key == '86238f77-0723-4470-a318-d59003553b62'
                messages = repositories.mentor_messages.find_all(
                    account.id, body['session']['id']
                )
                assert len(messages) == 1
                assert messages[0].content == 'Quero entender variáveis.'
            else:
                assert sessions.items == []
        with Session(postgres_database.engine) as session:
            events = session.scalars(select(EventModel)).all()
            if expected == 201:
                assert len(events) == 1
                assert events[0].name == 'intelligence/mentor.response.requested'
                assert events[0].payload == {
                    'attempt_id': response.json()['response']['attempt_id']
                }
            else:
                assert events == []

    @pytest.mark.parametrize('change', ['revision', 'deleted'])
    def test_default_access_rolls_back_creation_when_grant_becomes_invalid(
        self,
        postgres_database: 'PostgresDatabase',
        change: str,
    ) -> None:
        account = AccountFaker.fake(status=AccountStatus.ACTIVE)
        identity = SqlalchemyIdentityDatabase(engine=postgres_database.engine)
        with identity.transaction() as repositories:
            repositories.accounts.add(account)

        class ChangeAccessDuringTitle:
            def generate(self, first_message: str) -> str:
                del first_message
                if change == 'revision':
                    account.invalidate_other_accesses(account.updated_at)
                else:
                    account.delete(account.updated_at)
                with identity.transaction() as repositories:
                    repositories.accounts.update(account)
                return 'Título de teste'

        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            AuthenticatedUser(
                account_id=account.id,
                display_name=account.display_name,
                time_zone=None,
            )
        )
        app.dependency_overrides[
            IntelligencePipe.get_generate_mentor_title_workflow
        ] = ChangeAccessDuringTitle
        with TestClient(app, headers={'Authorization': 'Bearer synthetic'}) as http:
            response = http.post(
                '/intelligence/mentor-sessions',
                json={
                    'submission_key': '86238f77-0723-4470-a318-d59003553b62',
                    'first_message': 'Quero entender variáveis.',
                },
            )
        assert response.status_code == 403
        assert response.headers['cache-control'] == 'private, no-store'
        with SqlalchemyIntelligenceDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            assert (
                repositories.mentor_sessions.find_many(account.id, None, None).items
                == []
            )
            assert (
                repositories.mentor_sessions.find_submission(
                    account.id, '86238f77-0723-4470-a318-d59003553b62'
                )
                is None
            )
        with Session(postgres_database.engine) as session:
            assert session.scalars(select(EventModel)).all() == []

    @pytest.mark.parametrize(
        ('enabled', 'configured', 'constructor_fails', 'shutdown_fails'),
        [
            (False, True, False, False),
            (True, False, False, False),
            (True, True, True, False),
            (True, True, False, False),
            (True, True, False, True),
        ],
    )
    def test_optional_telemetry_does_not_change_private_history_response(
        self,
        postgres_database: 'PostgresDatabase',
        monkeypatch: pytest.MonkeyPatch,
        enabled: bool,
        configured: bool,
        constructor_fails: bool,
        shutdown_fails: bool,
    ) -> None:
        settings = get_settings().model_copy(
            update={
                'mentor_telemetry_enabled': enabled,
                'langfuse_public_key': SecretStr('synthetic-public')
                if configured
                else None,
                'langfuse_secret_key': SecretStr('synthetic-secret')
                if configured
                else None,
                'openrouter_api_key': None,
            }
        )
        client = Mock(spec=['shutdown'])
        if shutdown_fails:
            client.shutdown.side_effect = OSError('controlled telemetry shutdown')
        factory = Mock(return_value=client)
        if constructor_fails:
            factory.side_effect = OSError('controlled telemetry initialization')
        monkeypatch.setattr('shifu.app.get_settings', lambda: settings)
        monkeypatch.setattr('shifu.composition.mentor_telemetry.Langfuse', factory)
        app = FastAPIApp.register(postgres_database.engine)
        configure_mentor_access(app)
        app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            MENTOR_ACCOUNT
        )
        with TestClient(app, headers={'Authorization': 'Bearer synthetic'}) as http:
            response = http.get(
                '/intelligence/mentor-sessions/00000000000000000000000000'
            )
        assert response.status_code == 404
        assert response.headers['cache-control'] == 'private, no-store'
        if enabled and configured:
            assert settings.langfuse_public_key is not None
            assert settings.langfuse_secret_key is not None
            factory.assert_called_once_with(
                public_key=settings.langfuse_public_key.get_secret_value(),
                secret_key=settings.langfuse_secret_key.get_secret_value(),
                base_url=str(settings.langfuse_base_url).rstrip('/'),
                additional_headers={'x-langfuse-ingestion-version': '4'},
            )
        else:
            factory.assert_not_called()
        if enabled and configured and not constructor_fails:
            client.shutdown.assert_called_once_with()
        else:
            client.shutdown.assert_not_called()

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient
from agno.models.openai import OpenAIChat
from openai import OpenAI

from shifu.app import FastAPIApp
from shifu.intelligence.ai.generative.agno.workflows import (
    AgnoGenerateMentorTitleWorkflow,
)
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.providers.openrouter import MentorTitleModelProvider
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.pipes import SharedPipe
from shifu.shared.settings import Settings
from tests.intelligence.server.controllers.conftest import (
    MENTOR_ACCOUNT,
    MentorTitleWorkflowStub,
)

if TYPE_CHECKING:
    from httpx import Response
    import pytest
    from tests.fixtures.postgres_fixture import PostgresDatabase


class TestCreateMentorSessionController:
    def test_should_use_fallback_title_when_model_provider_is_unavailable(
        self,
        monkeypatch: pytest.MonkeyPatch,
        postgres_database: PostgresDatabase,
    ) -> None:
        def provide_no_title_model(_settings: Settings) -> None:
            return None

        monkeypatch.setattr(
            'shifu.app.MentorTitleModelProvider.build', provide_no_title_model
        )
        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            MENTOR_ACCOUNT
        )

        with TestClient(app, headers={'Authorization': 'Bearer test-token'}) as client:
            response = client.post(
                '/intelligence/mentor-sessions',
                json={
                    'submission_key': '3427141d-65bd-4862-a75d-123456789abc',
                    'first_message': '  fallback   title  ',
                },
            )

        assert response.status_code == 201
        assert response.json()['session']['title'] == 'fallback title'

    def test_should_close_configured_title_model_client_on_app_shutdown(
        self,
        monkeypatch: pytest.MonkeyPatch,
        postgres_database: PostgresDatabase,
    ) -> None:
        settings = Settings(
            redis_url='redis://localhost',
            openrouter_api_key='synthetic-test-key',
            mentor_title_prompt_logging_disabled=True,
        )
        model = MentorTitleModelProvider.build(settings)
        assert isinstance(model, OpenAIChat)
        model.client = OpenAI(
            api_key='synthetic-test-key', base_url='https://openrouter.ai/api/v1'
        )
        model_client = model.client

        def provide_title_model(_settings: Settings) -> OpenAIChat:
            return model

        monkeypatch.setattr(
            'shifu.app.MentorTitleModelProvider.build', provide_title_model
        )

        app = FastAPIApp.register(postgres_database.engine)

        with TestClient(app, headers={'Authorization': 'Bearer test-token'}):
            assert isinstance(
                app.state.generate_mentor_title_workflow,
                AgnoGenerateMentorTitleWorkflow,
            )

        assert model_client.is_closed

    def test_should_persist_exact_first_message_and_private_response(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        response = cast(
            'Response',
            mentor_client.post(
                '/intelligence/mentor-sessions',
                json={
                    'submission_key': '2a7e963f-d7dd-4cc9-9a46-8c650193f7a6',
                    'first_message': '  Olá, Mentor!\nQuero estudar.  ',
                },
            ),
        )

        assert response.status_code == 201
        assert response.headers['cache-control'] == 'private, no-store'
        body = response.json()
        assert body['session']['title'] == 'Conversa de teste'
        assert body['session']['id']
        assert body['pending_learner_message_id'] == body['messages']['items'][0]['id']
        assert (
            body['messages']['items'][0]['content']
            == '  Olá, Mentor!\nQuero estudar.  '
        )
        assert body['messages']['items'][0]['role'] == 'learner'
        assert 'account_id' not in body['session']
        assert 'submission_key' not in body['session']

        database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            persisted = repositories.mentor_sessions.find_submission(
                MENTOR_ACCOUNT.account_id, '2a7e963f-d7dd-4cc9-9a46-8c650193f7a6'
            )
            message_page = repositories.mentor_messages.find_many(
                MENTOR_ACCOUNT.account_id, body['session']['id'], None
            )
        assert persisted is not None
        assert persisted.session_id == body['session']['id']
        assert message_page.items[0].content == '  Olá, Mentor!\nQuero estudar.  '

    def test_should_replay_matching_submission_without_duplicate_content(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        request = {
            'submission_key': '1592b95a-0be9-4c7e-86cc-95f58e98d26f',
            'first_message': 'Mensagem original',
        }
        first = mentor_client.post('/intelligence/mentor-sessions', json=request)
        replay = cast(
            'Response',
            mentor_client.post('/intelligence/mentor-sessions', json=request),
        )

        assert first.status_code == 201
        assert replay.status_code == 200
        assert replay.json()['session']['id'] == first.json()['session']['id']
        database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            page = repositories.mentor_messages.find_many(
                MENTOR_ACCOUNT.account_id, first.json()['session']['id'], None
            )
        assert len(page.items) == 1

    def test_should_reject_unknown_body_fields_and_whitespace_message(
        self,
        mentor_client: TestClient,
    ) -> None:
        base = {
            'submission_key': 'bd12b0a2-54ae-4710-914b-8dc1ffb88978',
            'first_message': 'Mensagem válida',
        }
        extra_field = cast(
            'Response',
            mentor_client.post(
                '/intelligence/mentor-sessions', json={**base, 'account_id': 'forged'}
            ),
        )
        whitespace = cast(
            'Response',
            mentor_client.post(
                '/intelligence/mentor-sessions',
                json={**base, 'first_message': ' \n\t '},
            ),
        )

        assert extra_field.status_code == 422
        assert whitespace.status_code == 422
        assert extra_field.headers['cache-control'] == 'private, no-store'

    def test_should_conflict_when_a_submission_key_is_reused_for_changed_content(
        self, mentor_client: TestClient
    ) -> None:
        submission_key = '3e98064c-1259-4108-911a-609a2dfd7dc4'
        first = mentor_client.post(
            '/intelligence/mentor-sessions',
            json={'submission_key': submission_key, 'first_message': 'Primeiro texto'},
        )
        changed = cast(
            'Response',
            mentor_client.post(
                '/intelligence/mentor-sessions',
                json={'submission_key': submission_key, 'first_message': 'Outro texto'},
            ),
        )

        assert first.status_code == 201
        assert changed.status_code == 409
        assert changed.headers['cache-control'] == 'private, no-store'

    def test_should_create_once_for_matching_concurrent_submissions(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        second_app = FastAPIApp.register(postgres_database.engine)
        second_app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            MENTOR_ACCOUNT
        )
        second_app.dependency_overrides[
            IntelligencePipe.get_generate_mentor_title_workflow
        ] = MentorTitleWorkflowStub
        submission_key = '6c9cf961-a889-4e58-9cb4-b08ae689928c'
        payload = {'submission_key': submission_key, 'first_message': 'Concorrência'}
        barrier = Barrier(2)

        def submit(client: TestClient) -> Response:
            barrier.wait(timeout=5)
            return cast(
                'Response',
                client.post('/intelligence/mentor-sessions', json=payload),
            )

        with (
            TestClient(
                second_app, headers={'Authorization': 'Bearer test-token'}
            ) as second_client,
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            responses = list(executor.map(submit, [mentor_client, second_client]))

        assert sorted(response.status_code for response in responses) == [200, 201]
        assert (
            responses[0].json()['session']['id'] == responses[1].json()['session']['id']
        )
        database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            persisted = repositories.mentor_sessions.find_submission(
                MENTOR_ACCOUNT.account_id, submission_key
            )
            assert persisted is not None
            page = repositories.mentor_messages.find_many(
                MENTOR_ACCOUNT.account_id, persisted.session_id, None
            )
        assert len(page.items) == 1

    def test_should_create_once_for_concurrent_changed_content_with_same_key(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        second_app = FastAPIApp.register(postgres_database.engine)
        second_app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            MENTOR_ACCOUNT
        )
        second_app.dependency_overrides[
            IntelligencePipe.get_generate_mentor_title_workflow
        ] = MentorTitleWorkflowStub
        submission_key = '7b9a55d8-5666-4924-b3a9-5b5d2d83e38d'
        barrier = Barrier(2)

        def submit(client: TestClient, message: str) -> Response:
            barrier.wait(timeout=5)
            return cast(
                'Response',
                client.post(
                    '/intelligence/mentor-sessions',
                    json={'submission_key': submission_key, 'first_message': message},
                ),
            )

        with (
            TestClient(
                second_app, headers={'Authorization': 'Bearer test-token'}
            ) as second_client,
            ThreadPoolExecutor(max_workers=2) as executor,
        ):
            futures = (
                executor.submit(submit, mentor_client, 'Conteúdo A'),
                executor.submit(submit, second_client, 'Conteúdo B'),
            )
            responses = [future.result() for future in futures]

        assert sorted(response.status_code for response in responses) == [201, 409]
        database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
        with database.transaction() as repositories:
            persisted = repositories.mentor_sessions.find_submission(
                MENTOR_ACCOUNT.account_id, submission_key
            )
            assert persisted is not None
            page = repositories.mentor_messages.find_many(
                MENTOR_ACCOUNT.account_id, persisted.session_id, None
            )
        assert len(page.items) == 1

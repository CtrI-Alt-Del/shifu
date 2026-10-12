"""Registered job proof that configured OpenRouter stays unused in local-only scope."""

import json
import os
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import TYPE_CHECKING, Literal, cast
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI
from pydantic import HttpUrl
from sqlalchemy import select

import shifu.app as app_module
from shifu.app import FastAPIApp
from shifu.shared.settings import Settings
from shifu.intelligence.ai.agno.models.mentor_openai_chat import MentorOpenAIChat
from shifu.intelligence.database.sqlalchemy.models import (
    MentorMessageModel,
    MentorResponseAttemptModel,
    MentorResponseEventModel,
)
from shifu.intelligence.providers.openrouter.mentor_answer_model_provider import (
    OpenrouterMentorAnswerModelProvider,
)
from tests.messaging.inngest.jobs.intelligence.test_answer_mentor_message_job import (
    _publish_and_wait,  # pyright: ignore[reportPrivateUsage] - Existing native harness.
    _seed_request,  # pyright: ignore[reportPrivateUsage] - Existing native harness.
    controlled_mentor_endpoint as controlled_mentor_endpoint,
    create_mentor_test_app,
    prepared_mentor_index as prepared_mentor_index,
)

if TYPE_CHECKING:
    from shifu.intelligence.core.interfaces import (
        MentorRouteProvider,
        MentorTelemetryProvider,
    )
    from sqlalchemy import Engine
    from shifu.shared.core.interfaces import MentorAccessProvider, MentorContextProvider
    from tests.fixtures.inngest_fixture import InngestFixture
    from tests.messaging.inngest.jobs.intelligence.test_answer_mentor_message_job import (
        _ControlledInference,  # pyright: ignore[reportPrivateUsage] - Existing native harness.
    )


def create_openrouter_composition_app() -> FastAPI:
    original_register = FastAPIApp.register
    original_build = OpenrouterMentorAnswerModelProvider.build
    settings = app_module.get_settings().model_copy(
        update={
            'openrouter_api_key': 'disposable-test-key',
            'openrouter_prompt_logging_disabled': True,
            'openrouter_decisions_url': HttpUrl(
                f'{os.environ["SHIFU_MENTOR_TEST_ENDPOINT"]}/decisions'
            ),
            'mentor_telemetry_enabled': False,
        }
    )

    def controlled_model(
        settings: Settings,
        *,
        profile: Literal['primary', 'fallback', 'reviewer'] = 'primary',
    ) -> MentorOpenAIChat | None:
        model = original_build(settings, profile=profile)
        if model is not None and profile == 'reviewer':
            model.base_url = (
                f'{os.environ["SHIFU_MENTOR_OPENROUTER_TEST_ENDPOINT"]}/review/v1'
            )
        return model

    def register(database_engine: 'Engine | None' = None, **kwargs: object) -> FastAPI:
        # Omit the harness workflow so FastAPIApp constructs its production runtime.
        return original_register(
            database_engine,
            mentor_access_provider=cast(
                'MentorAccessProvider', kwargs['mentor_access_provider']
            ),
            mentor_route_provider=cast(
                'MentorRouteProvider', kwargs['mentor_route_provider']
            ),
            mentor_telemetry_provider=cast(
                'MentorTelemetryProvider', kwargs['mentor_telemetry_provider']
            ),
            mentor_context_provider=cast(
                'MentorContextProvider | None', kwargs.get('mentor_context_provider')
            ),
        )

    with (
        patch.object(FastAPIApp, 'register', side_effect=register),
        patch.object(
            OpenrouterMentorAnswerModelProvider, 'build', side_effect=controlled_model
        ),
        patch.object(app_module, 'get_settings', return_value=settings),
        patch.object(
            OpenrouterMentorAnswerModelProvider,
            '_BASE_URL',  # pyright: ignore[reportPrivateUsage] - Controlled transport origin only.
            f'{os.environ["SHIFU_MENTOR_OPENROUTER_TEST_ENDPOINT"]}/v1',
        ),
    ):
        return create_mentor_test_app()


@pytest.fixture(scope='session')
def inngest_app_target(
    controlled_mentor_endpoint: 'tuple[_ControlledInference, str]',
) -> Iterator[tuple[str, bool]]:
    state, upstream = controlled_mentor_endpoint

    class TransportHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            path = self.path
            if payload.get('model') == 'deepseek/deepseek-v4.1-flash':
                path = f'/fallback{path}'
            if (
                path == '/review/v1/chat/completions'
                and state.mode == 'agent_review_connection_drop'
            ):
                state.respond(path, payload)
                self.close_connection = True
                self.connection.close()
                return
            response = httpx.post(f'{upstream}{path}', json=payload, timeout=35)
            self.send_response(response.status_code)
            self.send_header(
                'Content-Type', response.headers.get('content-type', 'application/json')
            )
            self.send_header('Content-Length', str(len(response.content)))
            self.end_headers()
            self.wfile.write(response.content)

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    server = ThreadingHTTPServer(('127.0.0.1', 0), TransportHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    names = ('SHIFU_MENTOR_OPENROUTER_TEST_ENDPOINT', 'MENTOR_TELEMETRY_ENABLED')
    previous = {name: os.environ.get(name) for name in names}
    os.environ[names[0]] = f'http://127.0.0.1:{server.server_port}'
    os.environ[names[1]] = 'false'
    try:
        yield (
            'tests.messaging.inngest.jobs.intelligence.test_mentor_openrouter_composition_job:create_openrouter_composition_app',
            True,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@pytest.mark.usefixtures('prepared_mentor_index')
class TestMentorLocalOnlyCompositionJob:
    @pytest.mark.parametrize(
        ('question', 'expected_answer'),
        [
            (
                'O que é uma lista em Python?',
                (
                    'Uma lista em Python reúne elementos em uma sequência que pode ser '
                    'alterada. Os elementos têm posições, chamadas índices, começando em zero.'
                ),
            ),
            (
                'Como organizar meus estudos?',
                (
                    'Ainda não encontrei uma resposta local confiável para essa pergunta. '
                    'Tente perguntar sobre um Objetivo, uma Habilidade, seu progresso ou '
                    'um conteúdo do Currículo.'
                ),
            ),
        ],
        ids=('indexed-faq', 'local-abstention'),
    )
    def test_configured_openrouter_keeps_responses_local(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: 'tuple[_ControlledInference, str]',
        question: str,
        expected_answer: str,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        _, learner_id, attempt_id = _seed_request(inngest_fixture, question)
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        # Covers both writer chat completions and reviewer Decisions requests.
        assert state.requests == []
        assert not state.accounting_requests or all(
            row['used_tokens'] == 0 for row in state.accounting_requests
        )
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.status == 'completed'
            assert attempt.generation_keys == []
            assert attempt.usage_calls == []
            reply = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            )
            assert reply is not None and reply.content.endswith(expected_answer)
            events = session.scalars(
                select(MentorResponseEventModel).where(
                    MentorResponseEventModel.attempt_id == attempt_id
                )
            ).all()
            assert not any(
                (event.block_key or '').startswith('generated-') for event in events
            )

import json
from types import SimpleNamespace

import httpx2
import pytest
from agno.workflow.workflow import Workflow
from agno.models.openai import OpenAIChat
from openai import OpenAI

from shifu.intelligence.ai.generative.agno.agents.mentor_title_agent import (
    MentorTitleAgent,
)
from shifu.intelligence.ai.generative.agno.workflows.agno_generate_mentor_title_workflow import (
    AgnoGenerateMentorTitleWorkflow,
)
from shifu.intelligence.core.domain.errors import (
    MentorTitleOutputInvalidError,
    MentorTitleUnavailableError,
)
from shifu.intelligence.providers.openrouter import MentorTitleModelProvider
from shifu.shared.settings import Settings


class TestAgnoGenerateMentorTitleWorkflow:
    @staticmethod
    def _build_subject() -> tuple[AgnoGenerateMentorTitleWorkflow, OpenAI]:
        settings = Settings(
            redis_url='redis://localhost',
            openrouter_api_key='synthetic-test-key',
            mentor_title_prompt_logging_disabled=True,
        )
        model = MentorTitleModelProvider.build(settings)
        assert isinstance(model, OpenAIChat)
        client = OpenAI(
            api_key='synthetic-test-key',
            base_url='https://openrouter.ai/api/v1',
            max_retries=0,
            http_client=httpx2.Client(
                transport=httpx2.MockTransport(lambda request: httpx2.Response(500))
            ),
        )
        model.client = client
        return AgnoGenerateMentorTitleWorkflow(MentorTitleAgent(model)), client

    def test_should_send_one_private_structured_request_with_only_message_prefix(
        self,
    ) -> None:
        requests: list[httpx2.Request] = []

        def handle(request: httpx2.Request) -> httpx2.Response:
            requests.append(request)
            return httpx2.Response(
                200,
                json={
                    'id': 'chatcmpl-test',
                    'object': 'chat.completion',
                    'created': 1,
                    'model': 'openai/gpt-6-luna',
                    'choices': [
                        {
                            'index': 0,
                            'message': {
                                'role': 'assistant',
                                'content': json.dumps({'title': 'Título seguro'}),
                            },
                            'finish_reason': 'stop',
                        }
                    ],
                },
            )

        settings = Settings(
            redis_url='redis://localhost',
            openrouter_api_key='synthetic-test-key',
            mentor_title_prompt_logging_disabled=True,
        )
        model = MentorTitleModelProvider.build(settings)
        assert isinstance(model, OpenAIChat)
        client = OpenAI(
            api_key='synthetic-test-key',
            base_url='https://openrouter.ai/api/v1',
            max_retries=0,
            http_client=httpx2.Client(transport=httpx2.MockTransport(handle)),
        )
        model.client = client
        subject = AgnoGenerateMentorTitleWorkflow(MentorTitleAgent(model))
        first_message = '🙂' * 1000

        result = subject.generate(first_message)

        assert result == 'Título seguro'
        assert len(requests) == 1
        body = json.loads(requests[0].content)
        assert body['model'] == 'openai/gpt-6-luna'
        assert body['provider'] == {
            'zdr': True,
            'data_collection': 'deny',
            'require_parameters': True,
            'allow_fallbacks': False,
        }
        assert body['response_format']['type'] == 'json_schema'
        assert body['response_format']['json_schema']['strict'] is True
        assert len(body['messages']) == 2
        assert body['messages'][1]['content'] == first_message
        assert model.timeout == 3.0
        assert model.max_retries == 0
        assert model.retries == 0
        assert model.store is False
        client.close()

    def test_should_map_invalid_structured_output_without_retrying(self) -> None:
        requests: list[httpx2.Request] = []

        def handle(request: httpx2.Request) -> httpx2.Response:
            requests.append(request)
            return httpx2.Response(
                200,
                json={
                    'id': 'chatcmpl-invalid',
                    'object': 'chat.completion',
                    'created': 1,
                    'model': 'openai/gpt-6-luna',
                    'choices': [
                        {
                            'index': 0,
                            'message': {'role': 'assistant', 'content': '{"title":""}'},
                            'finish_reason': 'stop',
                        }
                    ],
                },
            )

        settings = Settings(
            redis_url='redis://localhost',
            openrouter_api_key='synthetic-test-key',
            mentor_title_prompt_logging_disabled=True,
        )
        model = MentorTitleModelProvider.build(settings)
        assert isinstance(model, OpenAIChat)
        client = OpenAI(
            api_key='synthetic-test-key',
            base_url='https://openrouter.ai/api/v1',
            max_retries=0,
            http_client=httpx2.Client(transport=httpx2.MockTransport(handle)),
        )
        model.client = client
        subject = AgnoGenerateMentorTitleWorkflow(MentorTitleAgent(model))

        with pytest.raises(MentorTitleOutputInvalidError):
            subject.generate('mensagem sintética')

        assert len(requests) == 1
        client.close()

    def test_should_map_provider_failure_without_retrying(self) -> None:
        requests: list[httpx2.Request] = []

        def handle(request: httpx2.Request) -> httpx2.Response:
            requests.append(request)
            return httpx2.Response(503, json={'error': {'message': 'offline'}})

        settings = Settings(
            redis_url='redis://localhost',
            openrouter_api_key='synthetic-test-key',
            mentor_title_prompt_logging_disabled=True,
        )
        model = MentorTitleModelProvider.build(settings)
        assert isinstance(model, OpenAIChat)
        client = OpenAI(
            api_key='synthetic-test-key',
            base_url='https://openrouter.ai/api/v1',
            max_retries=0,
            http_client=httpx2.Client(transport=httpx2.MockTransport(handle)),
        )
        model.client = client
        subject = AgnoGenerateMentorTitleWorkflow(MentorTitleAgent(model))

        with pytest.raises(MentorTitleUnavailableError):
            subject.generate('mensagem sintética')

        assert len(requests) == 1
        client.close()

    def test_should_not_build_model_without_logging_privacy_attestation(self) -> None:
        settings = Settings(
            redis_url='redis://localhost',
            openrouter_api_key='synthetic-test-key',
            mentor_title_prompt_logging_disabled=False,
        )

        assert MentorTitleModelProvider.build(settings) is None

    def test_should_not_build_model_without_openrouter_api_key(self) -> None:
        settings = Settings(
            redis_url='redis://localhost',
            openrouter_api_key=None,
            mentor_title_prompt_logging_disabled=True,
        )

        assert MentorTitleModelProvider.build(settings) is None

    def test_should_reject_incomplete_workflow_result_without_retrying(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        subject, client = self._build_subject()
        result = SimpleNamespace(has_completed=lambda: False, content=None)

        def run_incomplete(_workflow: Workflow, **_kwargs: object) -> SimpleNamespace:
            return result

        monkeypatch.setattr(Workflow, 'run', run_incomplete)

        with pytest.raises(MentorTitleUnavailableError):
            subject.generate('mensagem sintética')

        client.close()

    def test_should_validate_structured_content_returned_as_mapping(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        subject, client = self._build_subject()
        result = SimpleNamespace(
            has_completed=lambda: True, content={'title': 'Título tipado'}
        )

        def run_with_mapping(_workflow: Workflow, **_kwargs: object) -> SimpleNamespace:
            return result

        monkeypatch.setattr(Workflow, 'run', run_with_mapping)

        assert subject.generate('mensagem sintética') == 'Título tipado'

        client.close()

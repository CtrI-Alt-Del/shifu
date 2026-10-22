from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx
import httpx2
import pytest
from agno.agent import Agent
from agno.metrics import RunMetrics
from agno.models.openai import OpenAIChat
from agno.run.agent import RunOutput
from agno.run.base import RunStatus
from openai import APIStatusError
from pydantic import HttpUrl, ValidationError

from shifu.intelligence.ai import eval_factories as eval_factories_module
from shifu.intelligence.ai.eval_factories import (
    build_code_rubric_eval_provider,
    build_mentor_attachment_vision_eval_agent,
    build_mentor_title_eval_agent,
    build_process_mentor_response_eval_agents,
)
from shifu.intelligence.ai.agno.agents import (
    MentorAttachmentAnswerAgent,
    MentorAttachmentVisionAgent,
    MentorReviewerAgent,
    MentorTitleAgent,
)
from shifu.intelligence.ai.agno.outputs import (
    MentorAttachmentAnswerOutput,
    MentorAttachmentVisionOutput,
)
from shifu.intelligence.ai.data.mentor_inference_usage import (
    inference_guard_scope,
    inference_usage_scope,
)
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentUnavailableError,
)
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentChunk,
    MentorAttachmentContext,
    MentorAttachmentSource,
    MentorGenerationRequest,
    MentorInferenceUsage,
    MentorResponseBlock,
)
from shifu.shared.core.domain.structures import MentorContextSnapshot
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.intelligence.providers.openrouter.mentor_answer_model_provider import (
    OpenrouterMentorAnswerModelProvider,
)
from shifu.intelligence.providers.openrouter.mentor_title_model_provider import (
    MentorTitleModelProvider,
)
from shifu.shared.settings import Settings

if TYPE_CHECKING:
    from collections.abc import Callable

    from agno.models.base import Model


def _agent_run_response(response: RunOutput) -> Callable[..., RunOutput]:
    def run(_agent: Agent, *_args: object, **_kwargs: object) -> RunOutput:
        return response

    return run


def _settings() -> Settings:
    return Settings(
        redis_url='redis://127.0.0.1:6379',
        openrouter_api_key=None,
        openrouter_prompt_logging_disabled=False,
        mentor_title_prompt_logging_disabled=False,
    )


def test_eval_agent_factories_use_injected_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_provider_lookup(*_args: object, **_kwargs: object) -> None:
        raise AssertionError('Injected evaluation models must bypass runtime lookup')

    monkeypatch.setattr(MentorTitleModelProvider, 'build', unexpected_provider_lookup)
    monkeypatch.setattr(
        OpenrouterMentorAnswerModelProvider,
        'build',
        unexpected_provider_lookup,
    )
    title_model = OpenAIChat(id='eval-title', api_key='test-key')
    vision_model = OpenAIChat(id='eval-vision', api_key='test-key')
    answer_model = OpenAIChat(id='eval-answer', api_key='test-key')
    reviewer_model = OpenAIChat(id='eval-reviewer', api_key='test-key')

    title_agent = build_mentor_title_eval_agent(_settings(), model=title_model)
    vision_agent = build_mentor_attachment_vision_eval_agent(
        _settings(), model=vision_model
    )
    answer_agent, reviewer_agent = build_process_mentor_response_eval_agents(
        _settings(),
        answer_model=answer_model,
        reviewer_model=reviewer_model,
    )

    assert isinstance(title_agent, MentorTitleAgent)
    assert title_agent.model is title_model
    assert isinstance(vision_agent, MentorAttachmentVisionAgent)
    assert vision_agent.model is vision_model
    assert isinstance(answer_agent, MentorAttachmentAnswerAgent)
    assert answer_agent.model is answer_model
    assert isinstance(reviewer_agent, MentorReviewerAgent)
    assert reviewer_agent.model is reviewer_model


def test_title_eval_agent_fails_closed_when_no_model_is_configured() -> None:
    with pytest.raises(
        ServiceUnavailableError,
        match='Mentor title generation is unavailable',
    ):
        build_mentor_title_eval_agent(_settings())


def test_vision_eval_agent_fails_closed_when_no_model_is_configured() -> None:
    with pytest.raises(
        ServiceUnavailableError,
        match='Mentor attachment vision is unavailable',
    ):
        build_mentor_attachment_vision_eval_agent(_settings())


@pytest.mark.parametrize(
    ('answer_model', 'reviewer_model'),
    [
        (None, None),
        (OpenAIChat(id='eval-answer-only', api_key='test-key'), None),
        (None, OpenAIChat(id='eval-reviewer-only', api_key='test-key')),
    ],
)
def test_response_eval_agents_fail_closed_if_either_model_is_missing(
    answer_model: Model | None,
    reviewer_model: Model | None,
) -> None:
    with pytest.raises(
        ServiceUnavailableError,
        match='Mentor response generation is unavailable',
    ):
        build_process_mentor_response_eval_agents(
            _settings(),
            answer_model=answer_model,
            reviewer_model=reviewer_model,
        )


def test_code_rubric_eval_factory_passes_configured_transport_to_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        redis_url='redis://127.0.0.1:6379',
        openrouter_api_key='eval-api-key',
        openrouter_decisions_url=HttpUrl('https://eval.example.test/decisions'),
    )
    client = httpx.Client()
    captured: dict[str, object] = {}
    sentinel = object()

    def capture_provider(**kwargs: object) -> object:
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(
        eval_factories_module,
        'JevCodeRubricAssessorProvider',
        capture_provider,
    )
    try:
        provider = build_code_rubric_eval_provider(settings, client=client)
    finally:
        client.close()

    assert provider is sentinel
    assert captured == {
        'api_key': 'eval-api-key',
        'client': client,
        'decisions_url': 'https://eval.example.test/decisions',
        'model': 'typesafe/jev-1.13',
    }


def test_attachment_answer_agent_rejects_empty_requests_and_unapproved_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = MentorAttachmentAnswerAgent(
        OpenAIChat(id='eval-answer', api_key='test-key')
    )
    source = MentorAttachmentSource(
        attachment_id='A' * 26,
        chunk_id='B' * 26,
        page_number=1,
        locator='page:1',
    )
    chunk = MentorAttachmentChunk(
        chunk_id='B' * 26,
        attachment_id='A' * 26,
        generation=1,
        page_number=1,
        locator='page:1',
        content='Uma fração equivalente preserva a quantidade.',
    )
    context = MentorAttachmentContext(chunks=(chunk,), sources=(source,))

    with pytest.raises(MentorAttachmentUnavailableError):
        agent.answer('   ', context)
    with pytest.raises(MentorAttachmentUnavailableError):
        agent.answer(
            'Explique o trecho.', MentorAttachmentContext(chunks=(), sources=())
        )

    monkeypatch.setattr(
        Agent,
        'run',
        _agent_run_response(
            RunOutput(
                content={
                    'answer': 'A fração preserva o valor.',
                    'sources': [
                        {
                            'attachment_id': source.attachment_id,
                            'chunk_id': source.chunk_id,
                            'page_number': source.page_number,
                            'locator': 'page:9',
                        }
                    ],
                }
            )
        ),
    )
    usage: list[MentorInferenceUsage] = []
    with (
        inference_guard_scope(lambda: None),
        inference_usage_scope('answer', usage.append),
        pytest.raises(MentorAttachmentUnavailableError),
    ):
        agent.answer('Explique o trecho.', context)


def test_attachment_answer_agent_sanitizes_invalid_output_and_missing_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = MentorAttachmentAnswerAgent(
        OpenAIChat(id='eval-answer', api_key='test-key')
    )
    source = MentorAttachmentSource(
        attachment_id='C' * 26,
        chunk_id='D' * 26,
        page_number=1,
        locator='page:1',
    )
    chunk = MentorAttachmentChunk(
        chunk_id='D' * 26,
        attachment_id='C' * 26,
        generation=1,
        page_number=1,
        locator='page:1',
        content='The source text.',
    )
    context = MentorAttachmentContext(chunks=(chunk,), sources=(source,))
    output = {
        'answer': 'Grounded answer.',
        'sources': [
            {
                'attachment_id': source.attachment_id,
                'chunk_id': source.chunk_id,
                'page_number': source.page_number,
                'locator': source.locator,
            }
        ],
    }
    monkeypatch.setattr(Agent, 'run', _agent_run_response(RunOutput(content=output)))
    usage: list[MentorInferenceUsage] = []
    with (
        inference_guard_scope(lambda: None),
        inference_usage_scope('answer', usage.append),
    ):
        result = agent.answer('Summarize the source.', context)

    assert result.answer == 'Grounded answer.'
    assert result.sources[0].chunk_id == 'D' * 26
    assert len(usage) == 1

    monkeypatch.setattr(
        Agent,
        'run',
        _agent_run_response(RunOutput(content={'answer': ' ', 'sources': []})),
    )
    with (
        inference_guard_scope(lambda: None),
        inference_usage_scope('answer', usage.append),
        pytest.raises(MentorAttachmentUnavailableError),
    ):
        agent.answer('Summarize the source.', context)


@pytest.mark.parametrize(
    ('image_content', 'media_type', 'page_number'),
    [
        (b'', 'image/png', 1),
        (b'image', 'image/tiff', 1),
        (b'image', 'image/png', 0),
    ],
)
def test_attachment_vision_agent_rejects_invalid_image_boundaries(
    image_content: bytes,
    media_type: str,
    page_number: int,
) -> None:
    agent = MentorAttachmentVisionAgent(
        OpenAIChat(id='eval-vision', api_key='test-key')
    )
    with pytest.raises(MentorAttachmentUnavailableError):
        agent.analyze(
            image_content,
            media_type=media_type,
            attachment_id='attachment-3',
            page_number=page_number,
        )


def test_attachment_vision_agent_validates_output_and_suppresses_usage_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = MentorAttachmentVisionAgent(
        OpenAIChat(id='eval-vision', api_key='test-key')
    )
    monkeypatch.setattr(
        Agent,
        'run',
        _agent_run_response(
            RunOutput(
                content={'legible': True, 'description': 'Uma equação está visível.'}
            )
        ),
    )
    with inference_guard_scope(lambda: None):
        output = agent.analyze(
            b'image-bytes',
            media_type='image/png',
            attachment_id='attachment-3',
            page_number=1,
            usage_recorder=lambda _usage: (_ for _ in ()).throw(RuntimeError()),
        )
    assert output.legible
    assert output.description == 'Uma equação está visível.'

    monkeypatch.setattr(
        Agent,
        'run',
        _agent_run_response(RunOutput(content={'legible': True, 'description': ''})),
    )
    with (
        inference_guard_scope(lambda: None),
        pytest.raises(MentorAttachmentUnavailableError),
    ):
        agent.analyze(
            b'image-bytes',
            media_type='image/webp',
            attachment_id='attachment-3',
            page_number=1,
        )


def _review_request() -> tuple[MentorGenerationRequest, MentorResponseBlock]:
    context = MentorContextSnapshot(
        goal_id=None,
        skill_experience_id=None,
        skill_id=None,
        competency_id=None,
        activity_id=None,
        skill_completed=None,
        diagnostic_in_progress=False,
        facts=(),
        eligible_references=(),
        resolved_references=(),
        unavailable_sources=(),
    )
    request = MentorGenerationRequest(
        session_id='session-1',
        learner_message_id='message-1',
        attempt_id='attempt-1',
        requested_part='Explique a ideia.',
        history=(),
        context=context,
        approved_blocks=(),
        correction=None,
    )
    candidate = MentorResponseBlock(
        block_key='generated-0',
        ordinal=0,
        intent=None,
        content='Uma explicação educacional.',
    )
    return request, candidate


def _review_output(*, rejected: bool = False) -> dict[str, object]:
    return {
        key: {
            'choice': 'rejected' if rejected and key == 'fact_fidelity' else 'approved',
            'feedback': 'Ajuste o fato.' if rejected and key == 'fact_fidelity' else '',
        }
        for key in (
            'request_adherence',
            'fact_fidelity',
            'cumulative_solution',
            'diagnostic_safety',
            'privacy_access',
            'official_action_claims',
        )
    }


def test_reviewer_agent_maps_criteria_and_rejects_incomplete_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = MentorReviewerAgent(OpenAIChat(id='eval-reviewer', api_key='test-key'))
    request, candidate = _review_request()
    monkeypatch.setattr(
        Agent,
        'run',
        _agent_run_response(
            RunOutput(
                content=json.dumps(_review_output(rejected=True)),
                metrics=RunMetrics(input_tokens=2, output_tokens=3, total_tokens=5),
                status=RunStatus.completed,
            )
        ),
    )
    usage: list[MentorInferenceUsage] = []
    with (
        inference_guard_scope(lambda: None),
        inference_usage_scope('review', usage.append),
    ):
        result = agent.review(request, candidate)

    assert not result.approved
    assert result.correction == 'Revise a resposta: fact_fidelity: Ajuste o fato.'
    assert len(result.criteria) == 6
    assert len(usage) == 1

    monkeypatch.setattr(
        Agent,
        'run',
        _agent_run_response(RunOutput(content='not-json', status=RunStatus.completed)),
    )
    with (
        inference_guard_scope(lambda: None),
        inference_usage_scope('review', usage.append),
        pytest.raises(ServiceUnavailableError),
    ):
        agent.review(request, candidate)


def test_reviewer_agent_fails_closed_on_incomplete_run_and_records_provider_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = MentorReviewerAgent(OpenAIChat(id='eval-reviewer', api_key='test-key'))
    request, candidate = _review_request()
    monkeypatch.setattr(
        Agent,
        'run',
        _agent_run_response(
            RunOutput(
                content=_review_output(),
                metrics=RunMetrics(input_tokens=1, output_tokens=1, total_tokens=9),
                status=RunStatus.running,
            )
        ),
    )
    usage: list[MentorInferenceUsage] = []
    with (
        inference_guard_scope(lambda: None),
        inference_usage_scope('review', usage.append),
        pytest.raises(ServiceUnavailableError),
    ):
        agent.review(request, candidate)

    response = httpx2.Response(
        429,
        json={'usage': {'prompt_tokens': 2, 'completion_tokens': 3, 'total_tokens': 5}},
        request=httpx2.Request('POST', 'https://example.test'),
    )
    upstream_error = APIStatusError('rate limited', response=response, body=None)

    def fail_with_usage(_agent: Agent, *_args: object, **_kwargs: object) -> RunOutput:
        raise RuntimeError('private provider details') from upstream_error

    monkeypatch.setattr(Agent, 'run', fail_with_usage)
    with (
        inference_guard_scope(lambda: None),
        inference_usage_scope('review', usage.append),
        pytest.raises(ServiceUnavailableError) as error,
    ):
        agent.review(request, candidate)
    assert 'private provider details' not in str(error.value)
    assert usage[-1].used_tokens == 5


def test_attachment_output_schemas_reject_contradictory_content() -> None:
    with pytest.raises(ValidationError):
        MentorAttachmentAnswerOutput.model_validate(
            {'answer': '  ', 'sources': []}, strict=True
        )
    with pytest.raises(ValidationError):
        MentorAttachmentVisionOutput.model_validate(
            {'legible': True, 'description': '  '}, strict=True
        )

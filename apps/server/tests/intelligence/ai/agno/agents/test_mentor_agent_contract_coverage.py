from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from agno.agent import Agent
from agno.metrics import RunMetrics
from agno.run.base import RunStatus
import httpx
from openai import APIStatusError

from shifu.intelligence.ai.agno.agents.mentor_reviewer_agent import (
    MentorReviewerAgent,
)
from shifu.intelligence.ai.agno.outputs import (
    MentorAttachmentAnswerOutput,
    MentorAttachmentSourceOutput,
    MentorAttachmentVisionOutput,
)
from shifu.intelligence.ai.data.mentor_inference_usage import (
    inference_guard_scope,
    inference_usage_scope,
)
from shifu.intelligence.core.domain.structures import (
    MentorGenerationRequest,
    MentorResponseBlock,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError

if TYPE_CHECKING:
    from agno.models.base import Model


def test_attachment_outputs_reject_blank_and_inconsistent_content() -> None:
    with pytest.raises(ValueError):
        MentorAttachmentAnswerOutput(answer=' \n ', sources=[])

    source = MentorAttachmentSourceOutput(
        attachment_id='01J00000000000000000000000',
        chunk_id='01J00000000000000000000001',
        page_number=None,
        locator='chars:1-5#1',
    )
    with pytest.raises(ValueError):
        MentorAttachmentAnswerOutput(answer='answer', sources=[source, source] * 7)
    with pytest.raises(ValueError):
        MentorAttachmentVisionOutput(legible=True, description='  ')
    with pytest.raises(ValueError):
        MentorAttachmentVisionOutput(legible=False, description='readable text')


@dataclass
class _RequestContext:
    marker: str = 'authorized-context'


def _review_request() -> tuple[MentorGenerationRequest, MentorResponseBlock]:
    request = MentorGenerationRequest(
        session_id='01J00000000000000000000000',
        learner_message_id='01J00000000000000000000001',
        attempt_id='01J00000000000000000000002',
        requested_part='Explain lists',
        history=(),
        context=cast('object', _RequestContext()),
        approved_blocks=(),
        correction=None,
    )
    candidate = MentorResponseBlock(
        block_key='answer',
        ordinal=1,
        intent=None,
        content='A list stores items.',
        sources=(),
    )
    return request, candidate


def _review_content(
    choice: str = 'approved',
    feedback: str = '  clear  ',
    rejected_criteria: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        key: {
            'choice': 'rejected' if key in rejected_criteria else choice,
            'feedback': feedback,
        }
        for key in MentorReviewerAgent._CRITERIA  # noqa: SLF001 - test all closed criteria.
    }


def test_reviewer_maps_all_criteria_and_sanitizes_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Agent, '__init__', lambda _self, **_kwargs: None)
    monkeypatch.setattr(
        Agent,
        'run',
        lambda _self, _input: SimpleNamespace(
            status=RunStatus.completed,
            content=_review_content(),
            metrics=None,
        ),
    )
    agent = MentorReviewerAgent(cast('Model', object()))
    request, candidate = _review_request()
    usage: list[object] = []

    with (
        inference_guard_scope(lambda: None),
        inference_usage_scope('response', usage.append),
    ):
        result = agent.review(request, candidate)

    assert result.approved is True
    assert len(result.criteria) == 6
    assert result.correction is None
    assert result.feedback[0] == ('request_adherence', 'clear')
    assert len(usage) == 1


def test_reviewer_reports_rejected_criteria_with_fallback_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Agent, '__init__', lambda _self, **_kwargs: None)
    monkeypatch.setattr(
        Agent,
        'run',
        lambda _self, _input: SimpleNamespace(
            status=RunStatus.completed,
            content=_review_content(choice='rejected', feedback=' '),
            metrics=None,
        ),
    )
    agent = MentorReviewerAgent(cast('Model', object()))
    request, candidate = _review_request()

    with (
        inference_guard_scope(lambda: None),
        inference_usage_scope('response', lambda _u: None),
    ):
        result = agent.review(request, candidate)

    assert result.approved is False
    assert result.correction is not None
    assert 'Ajuste a resposta para satisfazer este critério.' in result.correction


def test_reviewer_maps_unsupported_claim_to_factual_correction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Agent, '__init__', lambda _self, **_kwargs: None)
    monkeypatch.setattr(
        Agent,
        'run',
        lambda _self, _input: SimpleNamespace(
            status=RunStatus.completed,
            content=_review_content(
                rejected_criteria=('fact_fidelity',),
                feedback='The claim conflicts with the approved source.',
            ),
            metrics=None,
        ),
    )
    agent = MentorReviewerAgent(cast('Model', object()))
    request, candidate = _review_request()

    with (
        inference_guard_scope(lambda: None),
        inference_usage_scope('response', lambda _usage: None),
    ):
        result = agent.review(request, candidate)

    assert result.approved is False
    assert result.criteria == (
        ('request_adherence', 'approved', None),
        ('fact_fidelity', 'rejected', None),
        ('cumulative_solution', 'approved', None),
        ('diagnostic_safety', 'approved', None),
        ('privacy_access', 'approved', None),
        ('official_action_claims', 'approved', None),
    )
    assert result.correction == (
        'Revise a resposta: fact_fidelity: '
        'The claim conflicts with the approved source.'
    )


def test_reviewer_sanitizes_transport_errors_and_extracts_failure_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Agent, '__init__', lambda _self, **_kwargs: None)

    def fail(_self: object, _input: object) -> None:
        raise RuntimeError('private provider detail')

    monkeypatch.setattr(Agent, 'run', fail)
    agent = MentorReviewerAgent(cast('Model', object()))
    request, candidate = _review_request()
    usage: list[object] = []

    with (
        inference_guard_scope(lambda: None),
        inference_usage_scope('response', usage.append),
        pytest.raises(ServiceUnavailableError) as raised,
    ):
        agent.review(request, candidate)

    assert 'private provider detail' not in str(raised.value)
    assert len(usage) == 1


def test_reviewer_usage_helpers_validate_metrics_and_failure_payloads() -> None:
    assert MentorReviewerAgent._usage(  # noqa: SLF001 - helper contract.
        SimpleNamespace(metrics=None)
    ) == (None, None, None, None)
    assert MentorReviewerAgent._usage(  # noqa: SLF001 - helper contract.
        SimpleNamespace(
            metrics=RunMetrics(
                input_tokens=2, output_tokens=3, total_tokens=5, cost=0.25
            )
        )
    ) == (2, 3, 5, 0.25)
    assert MentorReviewerAgent._usage(  # noqa: SLF001 - helper contract.
        SimpleNamespace(
            metrics=RunMetrics(input_tokens=2, output_tokens=3, total_tokens=7, cost=-1)
        )
    ) == (None, None, None, None)

    error = RuntimeError('transport')
    response = httpx.Response(
        400,
        json={'usage': {'prompt_tokens': 2, 'completion_tokens': 3, 'total_tokens': 5}},
        request=httpx.Request('POST', 'https://model.invalid'),
    )
    api_error = APIStatusError(
        'provider error',
        response=response,
        body=None,
    )
    error.__cause__ = api_error
    assert MentorReviewerAgent._failure_tokens(error) == 5  # noqa: SLF001

    inconsistent = RuntimeError('transport')
    inconsistent.__cause__ = APIStatusError(
        'provider error',
        response=httpx.Response(
            400,
            json={
                'usage': {
                    'prompt_tokens': 2,
                    'completion_tokens': 3,
                    'total_tokens': 6,
                }
            },
            request=httpx.Request('POST', 'https://model.invalid'),
        ),
        body=None,
    )
    assert MentorReviewerAgent._failure_tokens(inconsistent) is None  # noqa: SLF001


@pytest.mark.parametrize(
    'response',
    [
        SimpleNamespace(status=RunStatus.cancelled, content={}, metrics=None),
        SimpleNamespace(
            status=RunStatus.completed, content={'unexpected': 'shape'}, metrics=None
        ),
    ],
)
def test_reviewer_fails_closed_for_incomplete_run_or_invalid_schema(
    monkeypatch: pytest.MonkeyPatch,
    response: SimpleNamespace,
) -> None:
    monkeypatch.setattr(Agent, '__init__', lambda _self, **_kwargs: None)
    monkeypatch.setattr(Agent, 'run', lambda _self, _input: response)
    agent = MentorReviewerAgent(cast('Model', object()))
    request, candidate = _review_request()
    usage: list[object] = []

    with (
        inference_guard_scope(lambda: None),
        inference_usage_scope('response', usage.append),
        pytest.raises(ServiceUnavailableError),
    ):
        agent.review(request, candidate)

    assert len(usage) == 1


def test_reviewer_failure_tokens_rejects_malformed_provider_usage_payloads() -> None:
    request = httpx.Request('POST', 'https://model.invalid')
    responses = (
        httpx.Response(400, content=b'not-json', request=request),
        httpx.Response(400, json=['unexpected-body'], request=request),
        httpx.Response(400, json={'usage': []}, request=request),
        httpx.Response(
            400,
            json={
                'usage': {
                    'prompt_tokens': True,
                    'completion_tokens': 0,
                    'total_tokens': 1,
                }
            },
            request=request,
        ),
    )

    for response in responses:
        error = RuntimeError('transport')
        error.__cause__ = APIStatusError('provider error', response=response, body=None)

        assert MentorReviewerAgent._failure_tokens(error) is None  # noqa: SLF001

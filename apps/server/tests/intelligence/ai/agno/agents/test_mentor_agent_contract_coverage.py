from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

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
from shifu.shared.core.domain.structures import MentorContextSnapshot

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


def _review_request() -> tuple[MentorGenerationRequest, MentorResponseBlock]:
    request = MentorGenerationRequest(
        session_id='01J00000000000000000000000',
        learner_message_id='01J00000000000000000000001',
        attempt_id='01J00000000000000000000002',
        requested_part='Explain lists',
        history=(),
        context=MentorContextSnapshot(
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
        ),
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
        for key in (
            'request_adherence',
            'fact_fidelity',
            'cumulative_solution',
            'diagnostic_safety',
            'privacy_access',
            'official_action_claims',
        )
    }


def _stub_agent_init(monkeypatch: pytest.MonkeyPatch) -> None:
    def initialize(_self: Any, **_kwargs: Any) -> None:
        return

    monkeypatch.setattr(cast('Any', Agent), '__init__', initialize)


def _stub_agent(monkeypatch: pytest.MonkeyPatch, result: Any) -> None:
    def run(_self: Any, _input: Any) -> Any:
        return result

    _stub_agent_init(monkeypatch)
    monkeypatch.setattr(cast('Any', Agent), 'run', run)


def test_reviewer_maps_all_criteria_and_sanitizes_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_agent(
        monkeypatch,
        SimpleNamespace(
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
    _stub_agent(
        monkeypatch,
        SimpleNamespace(
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
    _stub_agent(
        monkeypatch,
        SimpleNamespace(
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
    _stub_agent_init(monkeypatch)

    def fail(_self: object, _input: object) -> None:
        raise RuntimeError('private provider detail')

    monkeypatch.setattr(cast('Any', Agent), 'run', fail)
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
    assert MentorReviewerAgent._usage(  # noqa: SLF001 - helper contract. # pyright: ignore[reportPrivateUsage]
        cast('Any', SimpleNamespace(metrics=None))
    ) == (None, None, None, None)
    assert MentorReviewerAgent._usage(  # noqa: SLF001 - helper contract. # pyright: ignore[reportPrivateUsage]
        cast(
            'Any',
            SimpleNamespace(
                metrics=RunMetrics(
                    input_tokens=2, output_tokens=3, total_tokens=5, cost=0.25
                )
            ),
        )
    ) == (2, 3, 5, 0.25)
    assert MentorReviewerAgent._usage(  # noqa: SLF001 - helper contract. # pyright: ignore[reportPrivateUsage]
        cast(
            'Any',
            SimpleNamespace(
                metrics=RunMetrics(
                    input_tokens=2, output_tokens=3, total_tokens=7, cost=-1
                )
            ),
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
        response=cast('Any', response),
        body=None,
    )
    error.__cause__ = api_error
    assert MentorReviewerAgent._failure_tokens(error) == 5  # noqa: SLF001 # pyright: ignore[reportPrivateUsage]

    inconsistent = RuntimeError('transport')
    inconsistent.__cause__ = APIStatusError(
        'provider error',
        response=cast(
            'Any',
            httpx.Response(
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
        ),
        body=None,
    )
    assert MentorReviewerAgent._failure_tokens(inconsistent) is None  # noqa: SLF001 # pyright: ignore[reportPrivateUsage]


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
    _stub_agent(monkeypatch, response)
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
        error.__cause__ = APIStatusError(
            'provider error', response=cast('Any', response), body=None
        )

        assert MentorReviewerAgent._failure_tokens(error) is None  # noqa: SLF001 # pyright: ignore[reportPrivateUsage]

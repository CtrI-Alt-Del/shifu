import asyncio
import json
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import httpx
import pytest

if TYPE_CHECKING:
    from fastapi import FastAPI

from shifu.learning.ai.learning_workflows_registry import LearningWorkflowsRegistry
from shifu.learning.core.domain.entities import ActivityAttempt
from shifu.learning.core.domain.enums import ActivityAttemptKind
from shifu.shared.core.domain.structures import (
    CodeRubricAssessmentInput,
    CurriculumChoiceActivitySnapshot,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumCodeInconclusiveCommentSnapshot,
    CurriculumCodeRubricCommentSnapshot,
    CurriculumCodeRubricCriterionSnapshot,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import OutboxEvent
from tests.fixtures.agentos_fixture import RegisteredAgentOSFixture

_NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)


def _event(name: str, payload: dict[str, object]) -> OutboxEvent:
    return OutboxEvent(
        id='event-1',
        name=name,
        payload=payload,
        destination='unrouted',
        status='pending',
        attempts=0,
        available_at=_NOW,
        reserved_by=None,
        reservation_expires_at=None,
        last_error_code=None,
        created_at=_NOW,
        updated_at=_NOW,
        published_at=None,
    )


def _assessment_request() -> CodeRubricAssessmentInput:
    criterion = CurriculumCodeRubricCriterionSnapshot(
        key='correctness',
        name='Corretude',
        description='Produza a saída solicitada.',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CurriculumCodeRubricCommentSnapshot(
                id=f'level-{level}',
                level=level,
                text=f'Comment {level}',
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CurriculumCodeInconclusiveCommentSnapshot(
            id='unknown',
            text='Não foi possível avaliar.',
        ),
    )
    return CodeRubricAssessmentInput(
        question_kind='javascript_stdin',
        prompt='Escreva um programa que imprima uma saudação.',
        project_files=(('src/main.js', "console.log('Olá')"),),
        submitted_paths=('src/main.js',),
        rubric_criteria=(criterion,),
        concept_criteria=(),
    )


def _attempt(
    attempt_id: str,
    snapshot: CurriculumChoiceActivitySnapshot | None,
) -> ActivityAttempt:
    return ActivityAttempt.create(
        id=attempt_id,
        skill_experience_id='experience-1',
        competency_id='competency-1',
        activity_id='activity-1',
        kind=ActivityAttemptKind.LEARNING,
        answers=(),
        submitted_at=_NOW,
        grading_snapshot=snapshot,
    )


def _registry_with_attempts(
    attempts: dict[str, ActivityAttempt],
) -> LearningWorkflowsRegistry:
    @contextmanager
    def transaction() -> Generator[SimpleNamespace]:
        yield SimpleNamespace(
            activity_attempts=SimpleNamespace(find_by_id=attempts.get)
        )

    registry = object.__new__(LearningWorkflowsRegistry)
    object.__setattr__(registry, '_database', SimpleNamespace(transaction=transaction))
    return registry


def _choice_snapshot() -> CurriculumChoiceActivitySnapshot:
    question = CurriculumChoiceQuestionSnapshot(
        key='q1',
        kind='single_choice',
        prompt='Which answer is correct?',
        options=(
            CurriculumChoiceOptionSnapshot(
                key='correct', text='The correct answer', is_correct=True
            ),
        ),
        correct_explanation='That is correct.',
        incorrect_explanation='Try again.',
    )
    return CurriculumChoiceActivitySnapshot(
        id='activity-1',
        competency_id='competency-1',
        difficulty='easy',
        title='Choice activity',
        questions=(question,),
        parts=(
            CurriculumChoicePartSnapshot(
                question_key='q1', weight_percentage=Decimal('100')
            ),
        ),
    )


@dataclass
class _ControlledJevEndpoint:
    requests: list[dict[str, object]] = field(default_factory=list)
    fail: bool = False

    def respond(self, request: httpx.Request) -> httpx.Response:
        payload = cast('dict[str, object]', json.loads(request.content))
        self.requests.append(payload)
        if self.fail:
            return httpx.Response(503, json={'detail': 'assessment unavailable'})

        raw_questions = payload.get('questions')
        questions = (
            cast('dict[str, object]', raw_questions)
            if isinstance(raw_questions, dict)
            else {}
        )
        answers: dict[str, dict[str, str]] = {}
        for question_id, raw_question in questions.items():
            if not isinstance(raw_question, dict):
                continue
            question = cast('dict[str, object]', raw_question)
            raw_criteria = question.get('criteria')
            if not isinstance(raw_criteria, dict):
                continue
            criteria = cast('dict[str, object]', raw_criteria)
            first_choice = next(iter(criteria), None)
            if isinstance(first_choice, str):
                answers[question_id] = {
                    'type': 'choice',
                    'choice': first_choice,
                }
        return httpx.Response(200, json={'answers': answers})

    def build_client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.respond))


@pytest.fixture(autouse=True)
def controlled_jev_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[_ControlledJevEndpoint]:
    endpoint = _ControlledJevEndpoint()

    monkeypatch.setattr(
        'shifu.intelligence.ai.intelligence_workflows_registry.IntelligenceWorkflowsRegistry._build_code_rubric_client',
        staticmethod(endpoint.build_client),
    )
    yield endpoint


class TestLearningCodeEvaluationWorkflow:
    def test_learning_event_projector_rejects_incomplete_events(self) -> None:
        name = 'learning/activity-submission.requested'

        assert (
            LearningWorkflowsRegistry._project_event(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                _event('another.event', {})
            )
            is None
        )
        assert (
            LearningWorkflowsRegistry._project_event(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                _event(name, {'attempt_id': 'attempt-1'})
            )
            is None
        )
        assert LearningWorkflowsRegistry._project_event(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            _event(name, {'attempt_id': 'attempt-1', 'run_id': 'run-1'})
        ) == (
            'learning-evaluate-code-activity',
            {'attempt_id': 'attempt-1', 'run_id': 'run-1'},
        )

    def test_learning_registry_routes_attempts_by_saved_snapshot_type(self) -> None:
        choice_attempt = _attempt('choice-attempt', _choice_snapshot())
        legacy_attempt = _attempt('legacy-attempt', None)
        registry = _registry_with_attempts(
            {
                choice_attempt.id: choice_attempt,
                legacy_attempt.id: legacy_attempt,
            }
        )
        event_name = 'learning/activity-submission.requested'

        assert registry.destination_for_event(_event('another.event', {})) is None
        assert registry.destination_for_event(_event(event_name, {})) is None
        assert (
            registry.destination_for_event(_event(event_name, {'attempt_id': 12}))
            is None
        )
        assert (
            registry.destination_for_event(_event(event_name, {'attempt_id': ''}))
            is None
        )
        assert (
            registry.destination_for_event(
                _event(event_name, {'attempt_id': 'missing-attempt'})
            )
            is None
        )
        assert (
            registry.destination_for_event(
                _event(event_name, {'attempt_id': choice_attempt.id})
            )
            == 'inngest'
        )
        assert (
            registry.destination_for_event(
                _event(event_name, {'attempt_id': legacy_attempt.id})
            )
            is None
        )

    def test_registered_agentos_handles_stale_runs_and_assessment_handoffs(
        self,
        controlled_jev_endpoint: _ControlledJevEndpoint,
        agentos_fixture: RegisteredAgentOSFixture,
    ) -> None:
        request = _assessment_request()
        application = cast('FastAPI', agentos_fixture.client.app)
        registry = application.state.learning_workflows_registry

        route_name = 'learning/activity-submission.requested'
        assert registry.destination_for_event(_event('another.event', {})) is None
        assert (
            registry.destination_for_event(_event(route_name, {'attempt_id': ''}))
            is None
        )
        assert (
            registry.destination_for_event(
                _event(route_name, {'attempt_id': 'missing-attempt'})
            )
            is None
        )

        stale_receipt = registry.client.submit_workflow(
            workflow_id='learning-evaluate-code-activity',
            fields={
                'attempt_id': 'missing-attempt',
                'run_id': 'missing-run',
            },
            background=False,
            session_id='learning-stale-attempt-test',
        )
        assert isinstance(stale_receipt.get('run_id'), str)

        decisions = registry.code_rubric_assessor.assess(request)

        assert decisions.criterion_levels[0].key == 'correctness'
        assert decisions.criterion_levels[0].level == 0
        assert decisions.concept_levels == ()
        assert len(controlled_jev_endpoint.requests) == 1
        raw_questions = controlled_jev_endpoint.requests[0].get('questions')
        assert isinstance(raw_questions, dict)
        questions = cast('dict[str, object]', raw_questions)
        assert tuple(questions) == ('rubric:correctness',)

        failure_request_start = len(controlled_jev_endpoint.requests)
        controlled_jev_endpoint.fail = True
        with pytest.raises(ServiceUnavailableError):
            registry.code_rubric_assessor.assess(request)

        # The registered workflow returns the terminal provider failure after
        # JEV's initial request and one configured retry for retryable 503s.
        assert len(controlled_jev_endpoint.requests) - failure_request_start == 2

    def test_registered_agentos_rejects_invalid_workflow_inputs_safely(
        self,
        controlled_jev_endpoint: _ControlledJevEndpoint,
        agentos_fixture: RegisteredAgentOSFixture,
    ) -> None:
        application = cast('FastAPI', agentos_fixture.client.app)
        registry = application.state.learning_workflows_registry

        for index, fields in enumerate(
            (
                {'attempt_id': 'missing-run-id'},
                {'handoff_ref': 'missing-handoff'},
            ),
            start=1,
        ):
            receipt = registry.client.submit_workflow(
                workflow_id='learning-evaluate-code-activity',
                fields=fields,
                background=False,
                session_id=f'learning-invalid-input-{index}',
            )
            assert isinstance(receipt.get('run_id'), str)

        assert controlled_jev_endpoint.requests == []

    def test_registered_assessor_fails_closed_when_agentos_client_is_unavailable(
        self,
        controlled_jev_endpoint: _ControlledJevEndpoint,
        agentos_fixture: RegisteredAgentOSFixture,
    ) -> None:
        application = cast('FastAPI', agentos_fixture.client.app)
        registry = application.state.learning_workflows_registry
        asyncio.run(registry.client.close())

        with pytest.raises(ServiceUnavailableError):
            registry.code_rubric_assessor.assess(_assessment_request())

        assert controlled_jev_endpoint.requests == []

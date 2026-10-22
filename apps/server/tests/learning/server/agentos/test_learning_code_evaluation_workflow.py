# pyright: reportPrivateUsage=false
import asyncio
import json
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

if TYPE_CHECKING:
    from fastapi import FastAPI

from shifu.learning.ai.learning_workflows_registry import LearningWorkflowsRegistry
from shifu.learning.ai.agno.workflows.evaluate_code_activity_workflow import (
    AgentOSCodeRubricAssessorProvider,
    EvaluateCodeActivityWorkflow,
)
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.learning.core.domain.entities import ActivityAttempt, ActivityEvaluation
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures import (
    CodeAnswer,
    CodeSubmittedFile,
    SingleChoiceAnswer,
)
from shifu.shared.core.domain.structures import (
    CodeRubricDecisions,
    CodeRubricAssessmentInput,
    CurriculumChoiceActivitySnapshot,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumCodeInconclusiveCommentSnapshot,
    CurriculumCodeRubricCommentSnapshot,
    CurriculumCodeRubricCriterionSnapshot,
    CurriculumCodeRubricPartSnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumReactQuestionSnapshot,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import OutboxEvent
from shifu.shared.messaging.agentos.agentos_handoff_store import AgentOSHandoffStore
from tests.fixtures.agentos_fixture import RegisteredAgentOSFixture
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.learning.core.use_cases.test_preview_activity_question_feedback_use_case import (
    mixed_snapshot,
)
from shifu.shared.database.seed_data import (
    SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS,
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
    build_development_seed,
)
from shifu.shared.settings import get_settings

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
    snapshot: CurriculumChoiceActivitySnapshot
    | CurriculumLearningActivitySnapshot
    | None,
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


@pytest.fixture
def large_project_agentos_fixture(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> RegisteredAgentOSFixture:
    monkeypatch.setenv('MAX_CODE_ASSESSMENT_INPUT_BYTES', str(512 * 1024))
    get_settings.cache_clear()
    return cast('RegisteredAgentOSFixture', request.getfixturevalue('agentos_fixture'))


class TestLearningCodeEvaluationWorkflow:
    @pytest.mark.parametrize(
        'kinds',
        ((), ('javascript_stdin',), ('react',), ('javascript_stdin', 'react')),
        ids=('choice-only', 'javascript', 'react', 'javascript-and-react'),
    )
    def test_should_route_code_snapshots_to_the_learning_agentos(
        self, kinds: tuple[str, ...]
    ) -> None:
        snapshot = mixed_snapshot(react='react' in kinds)
        choice = snapshot.questions[0]
        choice_part = snapshot.parts[0]
        questions = list(snapshot.questions[:2])
        parts = list(snapshot.parts[:2])
        if not kinds:
            questions.append(replace(choice, key='q3'))
            parts.append(
                replace(choice_part, question_key='q3', weight_percentage=Decimal(40))
            )
        elif len(kinds) == 2:
            javascript = mixed_snapshot().questions[-1]
            react = snapshot.questions[-1]
            assert isinstance(javascript, CurriculumJavascriptStdinQuestionSnapshot)
            assert isinstance(react, CurriculumReactQuestionSnapshot)
            rubric = snapshot.parts[-1]
            assert isinstance(rubric, CurriculumCodeRubricPartSnapshot)
            questions = [choice, replace(javascript, key='q2'), react]
            parts = [
                choice_part,
                replace(rubric, question_key='q2', weight_percentage=Decimal(30)),
                rubric,
            ]
        else:
            questions.append(snapshot.questions[-1])
            parts.append(snapshot.parts[-1])
        snapshot = replace(snapshot, questions=tuple(questions), parts=tuple(parts))
        attempt = _attempt('code-routing-attempt', snapshot)
        registry = _registry_with_attempts({attempt.id: attempt})

        destination = registry.destination_for_event(
            _event('learning/activity-submission.requested', {'attempt_id': attempt.id})
        )

        assert destination == ('agentos:learning' if kinds else 'inngest')

    def test_should_evaluate_a_persisted_react_attempt_through_registered_agentos(
        self,
        controlled_jev_endpoint: _ControlledJevEndpoint,
        large_project_agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        application = cast('FastAPI', large_project_agentos_fixture.client.app)
        registry: LearningWorkflowsRegistry = (
            application.state.learning_workflows_registry
        )
        seed = build_development_seed()
        with SqlalchemyCurriculumDatabase(
            postgres_database.engine
        ).transaction() as repositories:
            repositories.skills.add_many(list(seed.skills))
            repositories.skill_foundations.add_many(list(seed.skill_foundations))
            repositories.competencies.add_many(list(seed.competencies))
            repositories.concepts.add_many(list(seed.concepts))
            repositories.materials.add_many(list(seed.materials))
            repositories.activities.add_many(list(seed.activities))
            repositories.curriculum_sequences.add_many(list(seed.curriculum_sequences))
        snapshot = replace(
            mixed_snapshot(react=True),
            id=SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS[4],
            competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
        )
        files = (
            CodeSubmittedFile(
                path='src/main.tsx',
                content='export const App = () => <div>React marker</div>;'
                + 'é' * 140_000,
            ),
            CodeSubmittedFile(
                path='src/components/Extra.tsx',
                content='export const Extra = () => <span>Extra marker</span>',
            ),
        )
        attempt = ActivityAttempt.create(
            id='01SHF000000000000000000921',
            skill_experience_id=SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
            competency_id=snapshot.competency_id,
            activity_id=snapshot.id,
            kind=ActivityAttemptKind.LEARNING,
            answers=(
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                SingleChoiceAnswer(question_key='q2', selected_option_key='a'),
                CodeAnswer(question_key='q3', kind='react', files=files),
            ),
            submitted_at=_NOW,
            grading_snapshot=snapshot,
        )
        evaluation = ActivityEvaluation.create(
            id='01SHF000000000000000000922',
            attempt_id=attempt.id,
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=_NOW,
            run_id='react-agentos-run',
        )
        with registry.database.transaction() as repositories:
            repositories.goals.add_many(list(seed.goals))
            repositories.skill_experiences.add_many(list(seed.skill_experiences))
            repositories.competency_progresses.add_many(
                list(seed.competency_progresses)
            )
            experience = repositories.skill_experiences.find_by_id(
                SEED_ADAPTIVE_LAB_EXPERIENCE_ID
            )
            assert experience is not None
            experience.status = SkillExperienceStatus.LEARNING
            repositories.skill_experiences.update(experience)
            repositories.activity_attempts.add(attempt)
            repositories.activity_evaluations.add(evaluation)
        assert (
            registry.destination_for_event(
                _event(
                    'learning/activity-submission.requested', {'attempt_id': attempt.id}
                )
            )
            == 'agentos:learning'
        )

        registry.client.submit_workflow(
            workflow_id='learning-evaluate-code-activity',
            fields={'attempt_id': attempt.id, 'run_id': 'react-agentos-run'},
            background=False,
            session_id='learning-react-persisted-attempt',
        )

        with registry.database.transaction() as repositories:
            completed = repositories.activity_evaluations.find_by_attempt_id(attempt.id)
            saved = repositories.activity_attempts.find_by_id(attempt.id)
        assert completed is not None
        assert completed.status is ActivityEvaluationStatus.COMPLETED
        assert completed.score == Decimal(60)
        assert completed.effect_applied_at is not None
        assert saved is not None and saved.grading_snapshot == snapshot
        assert saved.answers[-1] == CodeAnswer(
            question_key='q3', kind='react', files=files
        )
        assert len(controlled_jev_endpoint.requests) == 1
        assessed_project = json.dumps(controlled_jev_endpoint.requests[0])
        assert 'React marker' in assessed_project
        assert 'Extra marker' in assessed_project
        assert 'src/fixed.css' in assessed_project

        registry.client.submit_workflow(
            workflow_id='learning-evaluate-code-activity',
            fields={'attempt_id': attempt.id, 'run_id': 'react-agentos-run'},
            background=False,
            session_id='learning-react-persisted-attempt-replay',
        )

        with registry.database.transaction() as repositories:
            replayed = repositories.activity_evaluations.find_by_attempt_id(attempt.id)
        assert replayed is not None
        assert replayed.status is ActivityEvaluationStatus.COMPLETED
        assert replayed.score == completed.score
        assert replayed.parts == completed.parts
        assert replayed.effect_applied_at == completed.effect_applied_at
        assert len(controlled_jev_endpoint.requests) == 1

    def test_workflow_deep_copy_preserves_dependencies_and_applies_updates(
        self,
    ) -> None:
        prepare = Mock()
        evaluate = Mock()
        fail = Mock()
        assessor = Mock()
        handoffs = AgentOSHandoffStore()
        workflow = EvaluateCodeActivityWorkflow(
            prepare, evaluate, fail, assessor, handoffs
        )
        workflow_any = cast('Any', workflow)
        workflow_any.db = object()

        copied = workflow.deep_copy()
        updated = workflow.deep_copy(update={'name': 'Updated Learning Workflow'})

        assert copied is not workflow
        assert copied.db is workflow.db
        assert updated.name == 'Updated Learning Workflow'
        assert updated._prepare_use_case is prepare  # noqa: SLF001

    def test_direct_workflow_run_hides_preparation_failures(self) -> None:
        prepare = Mock()
        prepare.execute.side_effect = RuntimeError('private persistence detail')
        evaluate = Mock()
        workflow = EvaluateCodeActivityWorkflow(
            prepare, evaluate, Mock(), Mock(), AgentOSHandoffStore()
        )

        workflow.run(input={'attempt_id': 'attempt-1', 'run_id': 'run-1'})

        evaluate.execute.assert_not_called()

    def test_direct_workflow_run_hides_missing_handoff(self) -> None:
        assessor = Mock()
        evaluate = Mock()
        workflow = EvaluateCodeActivityWorkflow(
            Mock(), evaluate, Mock(), assessor, AgentOSHandoffStore()
        )

        workflow.run(input={'handoff_ref': 'unknown-handoff-reference-123'})

        assessor.assess.assert_not_called()
        evaluate.execute.assert_not_called()

    def test_direct_workflow_run_completes_failed_handoff_as_unavailable(self) -> None:
        assessment = _assessment_request()
        handoffs = AgentOSHandoffStore()
        reference = handoffs.create(
            capability='learning-code-assessment', input_value=assessment
        )
        assessor = Mock()
        assessor.assess.side_effect = RuntimeError('private provider detail')
        workflow = EvaluateCodeActivityWorkflow(
            Mock(), Mock(), Mock(), assessor, handoffs
        )

        workflow.run(input={'handoff_ref': reference})

        assert (
            handoffs.take_result(reference, capability='learning-code-assessment')
            == 'unavailable'
        )

    def test_assessor_adapter_discards_failed_and_rejects_missing_results(self) -> None:
        assessment = _assessment_request()
        handoffs = AgentOSHandoffStore()
        failed_client = Mock()
        failed_client.submit_workflow.side_effect = RuntimeError('private detail')
        provider = AgentOSCodeRubricAssessorProvider(failed_client, handoffs)

        with pytest.raises(
            ServiceUnavailableError, match='Code assessment is unavailable'
        ):
            provider.assess(assessment)
        failed_reference = failed_client.submit_workflow.call_args.kwargs['fields'][
            'handoff_ref'
        ]
        with pytest.raises(KeyError):
            handoffs.read_input(failed_reference, capability='learning-code-assessment')

        empty_client = Mock()
        empty_client.submit_workflow.return_value = None
        provider = AgentOSCodeRubricAssessorProvider(empty_client, handoffs)
        with pytest.raises(
            ServiceUnavailableError, match='Code assessment is unavailable'
        ):
            provider.assess(assessment)

    def test_learning_registry_properties_lifespan_and_idempotent_close(self) -> None:
        registry = object.__new__(LearningWorkflowsRegistry)
        runtime = SimpleNamespace(
            client=object(),
            observability=object(),
            start=AsyncMock(),
            close=AsyncMock(),
        )
        handoffs = Mock()
        database = object()
        assessor = object()
        object.__setattr__(registry, '_runtime', runtime)
        object.__setattr__(registry, '_observability', runtime.observability)
        object.__setattr__(registry, '_handoffs', handoffs)
        object.__setattr__(registry, '_database_port', database)
        object.__setattr__(registry, '_assessment_provider', assessor)
        object.__setattr__(registry, '_closed', False)

        assert registry.client is runtime.client
        assert registry.database is database
        assert registry.code_rubric_assessor is assessor
        assert registry.observability is runtime.observability

        async def run_lifespan() -> None:
            async with registry.lifespan():
                pass

        asyncio.run(run_lifespan())
        asyncio.run(registry.close())

        runtime.start.assert_awaited_once()
        runtime.close.assert_awaited_once()
        handoffs.clear.assert_called_once()

    def test_learning_registry_closes_after_runtime_start_failure(self) -> None:
        registry = object.__new__(LearningWorkflowsRegistry)
        runtime = SimpleNamespace(
            start=AsyncMock(side_effect=RuntimeError('runtime unavailable')),
            close=AsyncMock(),
        )
        handoffs = Mock()
        object.__setattr__(registry, '_runtime', runtime)
        object.__setattr__(registry, '_handoffs', handoffs)
        object.__setattr__(registry, '_closed', False)

        async def run_lifespan() -> None:
            async with registry.lifespan():
                pytest.fail('runtime startup should fail')

        with pytest.raises(RuntimeError, match='runtime unavailable'):
            asyncio.run(run_lifespan())

        runtime.close.assert_awaited_once()
        handoffs.clear.assert_called_once()

    def test_learning_registry_without_runtime_fails_closed(self) -> None:
        registry = object.__new__(LearningWorkflowsRegistry)
        handoffs = Mock()
        object.__setattr__(registry, '_runtime', None)
        object.__setattr__(registry, '_observability', None)
        object.__setattr__(registry, '_handoffs', handoffs)
        object.__setattr__(registry, '_closed', False)

        with pytest.raises(ServiceUnavailableError):
            _ = registry.client
        assert registry.observability is None

        async def run_lifespan() -> None:
            async with registry.lifespan():
                pytest.fail('lifespan should not start without an AgentOS runtime')

        with pytest.raises(ServiceUnavailableError):
            asyncio.run(run_lifespan())
        asyncio.run(registry.close())
        handoffs.clear.assert_called_once()

    def test_unavailable_learning_assessor_returns_safe_error(self) -> None:
        from shifu.learning.ai.learning_workflows_registry import (
            _UnavailableCodeRubricAssessorProvider,
        )

        with pytest.raises(
            ServiceUnavailableError, match='Code assessment is unavailable'
        ):
            _UnavailableCodeRubricAssessorProvider().assess(_assessment_request())

    def test_agentos_assessor_consumes_a_workflow_handoff_result(self) -> None:
        handoffs = AgentOSHandoffStore()
        decisions = CodeRubricDecisions(criterion_levels=(), concept_levels=())
        client = Mock()

        def complete_handoff(**kwargs: object) -> None:
            fields = cast('dict[str, str]', kwargs['fields'])
            handoffs.complete(
                fields['handoff_ref'],
                capability='learning-code-assessment',
                result_value=decisions,
            )

        client.submit_workflow.side_effect = complete_handoff
        provider = AgentOSCodeRubricAssessorProvider(client, handoffs)

        assert provider.assess(_assessment_request()) == decisions
        client.submit_workflow.assert_called_once()

    def test_direct_workflow_run_leaves_stale_attempt_unchanged(self) -> None:
        prepare = Mock()
        prepare.execute.return_value = None
        evaluate = Mock()
        fail = Mock()
        assessor = Mock()
        workflow = EvaluateCodeActivityWorkflow(
            prepare,
            evaluate,
            fail,
            assessor,
            AgentOSHandoffStore(),
        )

        workflow.run(input={'attempt_id': 'attempt-1', 'run_id': 'run-1'})

        assessor.assess.assert_not_called()
        evaluate.execute.assert_not_called()
        fail.execute.assert_not_called()

    def test_direct_workflow_run_rejects_malformed_input_safely(self) -> None:
        workflow = EvaluateCodeActivityWorkflow(
            Mock(), Mock(), Mock(), Mock(), AgentOSHandoffStore()
        )

        with pytest.raises(
            ServiceUnavailableError, match='Code assessment is unavailable'
        ):
            workflow.run(input={'attempt_id': 'attempt-1'})

    def test_direct_workflow_run_completes_assessment_handoff(self) -> None:
        assessment = _assessment_request()
        handoffs = AgentOSHandoffStore()
        reference = handoffs.create(
            capability='learning-code-assessment', input_value=assessment
        )
        assessor = Mock()
        decisions = CodeRubricDecisions(criterion_levels=(), concept_levels=())
        assessor.assess.return_value = decisions
        workflow = EvaluateCodeActivityWorkflow(
            Mock(), Mock(), Mock(), assessor, handoffs
        )

        workflow.run(input={'handoff_ref': reference})

        assessor.assess.assert_called_once_with(assessment)
        assert (
            handoffs.take_result(reference, capability='learning-code-assessment')
            == decisions
        )

    def test_direct_workflow_run_completes_invalid_handoff_as_unavailable(self) -> None:
        handoffs = AgentOSHandoffStore()
        reference = handoffs.create(
            capability='learning-code-assessment', input_value=object()
        )
        assessor = Mock()
        workflow = EvaluateCodeActivityWorkflow(
            Mock(), Mock(), Mock(), assessor, handoffs
        )

        workflow.run(input={'handoff_ref': reference})

        assessor.assess.assert_not_called()

    def test_direct_workflow_run_prepares_assesses_and_applies_code_decisions(
        self,
    ) -> None:
        assessment = _assessment_request()
        prepare = Mock()
        prepare.execute.return_value = SimpleNamespace(
            attempt_id='attempt-1',
            run_id='run-1',
            questions=(
                SimpleNamespace(question_key='question-1', assessment_input=assessment),
            ),
        )
        evaluate = Mock()
        fail = Mock()
        assessor = Mock()
        assessor.assess.return_value = object()
        workflow = EvaluateCodeActivityWorkflow(
            prepare,
            evaluate,
            fail,
            assessor,
            AgentOSHandoffStore(),
        )

        workflow.run(input={'attempt_id': 'attempt-1', 'run_id': 'run-1'})

        prepare.execute.assert_called_once_with('attempt-1', 'run-1')
        assessor.assess.assert_called_once_with(assessment)
        evaluate.execute.assert_called_once()
        fail.execute.assert_not_called()

    def test_direct_workflow_emits_completion_only_after_commit(self) -> None:
        assessment = _assessment_request()
        prepare = Mock()
        prepare.execute.return_value = SimpleNamespace(
            attempt_id='attempt-1',
            run_id='run-1',
            questions=(
                SimpleNamespace(question_key='question-1', assessment_input=assessment),
            ),
        )
        evaluate = Mock()
        evaluate.execute.side_effect = [False, True]
        telemetry = Mock()
        assessor = Mock()
        assessor.assess.return_value = object()
        workflow = EvaluateCodeActivityWorkflow(
            prepare,
            evaluate,
            Mock(),
            assessor,
            AgentOSHandoffStore(),
            telemetry_provider=telemetry,
        )

        workflow.run(input={'attempt_id': 'attempt-1', 'run_id': 'run-1'})
        telemetry.emit.assert_not_called()

        workflow.run(input={'attempt_id': 'attempt-1', 'run_id': 'run-1'})
        telemetry.emit.assert_called_once_with(
            {
                'level': 'INFO',
                'event': 'learning.evaluation.completed',
                'run_id': 'run-1',
                'operation': 'evaluation.complete',
                'result': 'success',
            }
        )

    def test_direct_workflow_run_fails_closed_when_assessment_fails(self) -> None:
        assessment = _assessment_request()
        prepare = Mock()
        prepare.execute.return_value = SimpleNamespace(
            attempt_id='attempt-1',
            run_id='run-1',
            questions=(
                SimpleNamespace(question_key='question-1', assessment_input=assessment),
            ),
        )
        evaluate = Mock()
        fail = Mock()
        assessor = Mock()
        assessor.assess.side_effect = RuntimeError('private provider detail')
        workflow = EvaluateCodeActivityWorkflow(
            prepare,
            evaluate,
            fail,
            assessor,
            AgentOSHandoffStore(),
        )

        workflow.run(input={'attempt_id': 'attempt-1', 'run_id': 'run-1'})

        fail.execute.assert_called_once_with('attempt-1', 'run-1')
        evaluate.execute.assert_not_called()

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

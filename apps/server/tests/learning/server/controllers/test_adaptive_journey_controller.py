"""Persisted HTTP journey for an eligible adaptive Skill in disposable PostgreSQL."""

from collections.abc import Callable, Iterator
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import func, select

from shifu.app import FastAPIApp
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.core.domain.structures import (
    JavascriptStdinQuestion,
    MultipleSelectionQuestion,
    SingleChoiceQuestion,
)
from shifu.curriculum.providers.curriculum_content_provider import (
    DatabaseCurriculumContentProvider,
)
from shifu.learning.core.use_cases.evaluate_choice_activity_use_case import (
    EvaluateChoiceActivityUseCase,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.database.sqlalchemy.models import (
    ConceptObservationModel,
    ConceptStateModel,
    SkillExperienceModel,
)
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser, RateLimitDecision
from shifu.shared.core.domain.structures import (
    CodeConceptDecision,
    CodeCriterionDecision,
    CodeRubricAssessmentInput,
    CodeRubricDecisions,
)
from shifu.shared.core.domain.structures.code_rubric_decisions import CodeRubricLevel
from shifu.shared.database.seed import seed as seed_database
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ADAPTIVE_CONCEPT_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS,
    SEED_ADAPTIVE_LAB_CONDITIONS_CONCEPT_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID,
    SEED_ADAPTIVE_LAB_BOOLEAN_CONCEPT_ID,
    SEED_ADAPTIVE_LAB_BOOLEAN_ACTIVITY_IDS,
    SEED_ADAPTIVE_LAB_BOOLEAN_MATERIAL_ID,
    SEED_ADAPTIVE_LAB_GOAL_ID,
    SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_PRIORITY_CONCEPT_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
    SEED_ADAPTIVE_SKILL_ID,
    build_development_seed,
)
from shifu.shared.database.sqlalchemy.settings import SeedSettings
from shifu.shared.database.sqlalchemy.models import EventModel
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture


class _Authentication:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=SEED_ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
        )


class _NoopBroker:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class _UnlimitedCache:
    async def consume_rate_limit_token(
        self, key: str, capacity: int, refill_per_second: float
    ) -> RateLimitDecision:
        return RateLimitDecision(allowed=True, retry_after_seconds=0)


class _FixedCodeRubricAssessor:
    def __init__(self, score: CodeRubricLevel = 75) -> None:
        self._score: CodeRubricLevel = score

    def assess(self, request: CodeRubricAssessmentInput) -> CodeRubricDecisions:
        return CodeRubricDecisions(
            criterion_levels=tuple(
                CodeCriterionDecision(key=item.key, level=self._score)
                for item in request.rubric_criteria
            ),
            concept_levels=tuple(
                CodeConceptDecision(concept_id=item.concept_id, level=self._score)
                for item in request.concept_criteria
            ),
        )


def _get(client: TestClient, path: str, headers: dict[str, str]) -> Response:
    return cast('Response', client.get(path, headers=headers))  # pyright: ignore[reportUnknownMemberType]


def _post(
    client: TestClient,
    path: str,
    headers: dict[str, str],
    payload: dict[str, object] | None = None,
) -> Response:
    return cast(
        'Response',
        client.post(path, headers=headers, json=payload),  # pyright: ignore[reportUnknownMemberType]
    )


def _practice_until_mastered(
    client: TestClient,
    skill_path: str,
    headers: dict[str, str],
    submit_and_evaluate: Callable[..., object],
) -> tuple[set[str], set[str]]:
    practiced: set[str] = set()
    targeted: set[str] = set()
    for _ in range(24):
        detail = _get(
            client,
            f'{skill_path}/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}',
            headers,
        )
        assert detail.status_code == 200, detail.text
        current = cast('dict[str, Any]', detail.json())
        if current['status'] == 'mastered':
            break
        target_id = current['adaptive']['targetConceptId']
        assert target_id in {
            SEED_ADAPTIVE_LAB_CONDITIONS_CONCEPT_ID,
            SEED_ADAPTIVE_LAB_BOOLEAN_CONCEPT_ID,
        }
        if (
            target_id == SEED_ADAPTIVE_LAB_BOOLEAN_CONCEPT_ID
            and target_id not in targeted
        ):
            assert current['adaptive']['materialId'] == (
                SEED_ADAPTIVE_LAB_BOOLEAN_MATERIAL_ID
            )
        targeted.add(target_id)
        activity_id = current['adaptive']['activityId']
        practiced.add(activity_id)
        submit_and_evaluate(
            client,
            skill_path,
            SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            activity_id,
            correct=True,
        )
    else:
        pytest.fail('Laboratory did not reach first-Competency mastery')
    return practiced, targeted


@pytest.fixture
def adaptive_app(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    seed = build_development_seed()
    curriculum = SqlalchemyCurriculumDatabase(postgres_database.engine)
    with curriculum.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
        repositories.competencies.add_many(list(seed.competencies))
        repositories.concepts.add_many(list(seed.concepts))
        repositories.materials.add_many(list(seed.materials))
        repositories.activities.add_many(list(seed.activities))
        repositories.curriculum_sequences.add_many(list(seed.curriculum_sequences))
    app = FastAPIApp.register(postgres_database.engine)
    app.state.authentication_provider = _Authentication()
    app.state.inngest_broker = _NoopBroker()
    yield app
    app.dependency_overrides.clear()


def test_adaptive_creation_diagnostic_privacy_and_persisted_baseline(
    adaptive_app: FastAPI,
    postgres_database: PostgresDatabase,
) -> None:
    headers = {'Authorization': 'Bearer test-access-token'}
    learning = SqlalchemyLearningDatabase(postgres_database.engine)
    provider = DatabaseCurriculumContentProvider(
        SqlalchemyCurriculumDatabase(postgres_database.engine)
    )
    with TestClient(adaptive_app, raise_server_exceptions=True) as client:
        adaptive_app.state.cache_provider = _UnlimitedCache()
        available = _get(client, '/learning/available-skills', headers)
        assert available.status_code == 200, available.text
        skills = cast('dict[str, Any]', available.json())['skills']
        assert any(
            item['id'] == SEED_ADAPTIVE_SKILL_ID and item['available']
            for item in skills
        )

        created = _post(
            client,
            '/learning/goals',
            headers,
            {
                'title': 'Aprender decisões',
                'description': 'Praticar condições com evidência por Conceito.',
                'skillIds': [SEED_ADAPTIVE_SKILL_ID],
            },
        )
        assert created.status_code == 201, created.text
        goal_id = cast('dict[str, Any]', created.json())['goalId']
        skill_path = f'/learning/goals/{goal_id}/skills/{SEED_ADAPTIVE_SKILL_ID}'
        with postgres_database.engine.connect() as connection:
            persisted_experience_id = connection.scalar(
                select(SkillExperienceModel.id).where(
                    SkillExperienceModel.goal_id == goal_id
                )
            )
        assert persisted_experience_id is not None

        diagnostic_run_id = str(uuid4())
        started = _post(
            client,
            f'{skill_path}/start',
            headers,
            {'entry_key': diagnostic_run_id},
        )
        assert started.status_code == 200, started.text
        diagnostic_headers = {**headers, 'X-Diagnostic-Run-Id': diagnostic_run_id}
        visited: list[str] = []
        diagnostic_items: list[dict[str, object]] = []
        overview = _get(client, f'{skill_path}/diagnostic', diagnostic_headers)
        assert overview.status_code == 200, overview.text
        data = cast('dict[str, Any]', overview.json())
        assert data['status'] == 'diagnosing'
        assert data['competencies'] == []
        assert data['pendingAttemptId'] is None
        activity_sequence = cast('list[dict[str, Any]]', data['activitySequence'])
        assert len(activity_sequence) == 3
        for index, expected_difficulty in enumerate(('easy', 'medium', 'hard')):
            sequence_item = activity_sequence[index]
            competency_id = sequence_item['competencyId']
            activity_id = sequence_item['activityId']
            assert activity_id not in visited
            visited.append(activity_id)
            activity_path = (
                f'{skill_path}/competencies/{competency_id}/activities/{activity_id}'
            )
            activity = _get(client, activity_path, diagnostic_headers)
            assert activity.status_code == 200, activity.text
            activity_data = cast('dict[str, Any]', activity.json())
            assert activity_data['is_diagnostic'] is True
            assert activity_data['difficulty'] == expected_difficulty
            answers = [
                {
                    'question_key': question['key'],
                    'kind': question['kind'],
                    'selected_option_keys': ['a'],
                }
                for question in activity_data['questions']
            ]
            diagnostic_items.append(
                {
                    'competency_id': competency_id,
                    'activity_id': activity_id,
                    'activity_revision': activity_data['activity_revision'],
                    'answers': answers,
                }
            )

        submitted = _post(
            client,
            f'{skill_path}/diagnostic/submissions',
            diagnostic_headers,
            {'submission_key': str(uuid4()), 'items': diagnostic_items},
        )
        assert submitted.status_code == 201, submitted.text
        assert submitted.json() == {'status': 'pending', 'replayed': False}
        pending = cast(
            'dict[str, Any]',
            _get(client, f'{skill_path}/diagnostic', diagnostic_headers).json(),
        )
        assert pending['pendingAttemptId'] is not None
        assert pending['pendingAttemptStatus'] == 'pending'
        with learning.transaction() as repositories:
            diagnostic_attempts = repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id(
                persisted_experience_id, diagnostic_run_id
            )
            pending_evaluations = tuple(
                repositories.activity_evaluations.find_by_attempt_id(attempt.id)
                for attempt in diagnostic_attempts
            )
        assert len(diagnostic_attempts) == len(visited)
        for attempt in diagnostic_attempts:
            activity_path = (
                f'{skill_path}/competencies/{attempt.competency_id}'
                f'/activities/{attempt.activity_id}'
            )
            private_result = _get(
                client, f'{activity_path}/attempts/{attempt.id}', headers
            )
            assert private_result.status_code == 404
        for evaluation in pending_evaluations:
            assert evaluation is not None
            assert evaluation.status.value == 'pending'
            assert evaluation.run_id is not None
        for attempt, evaluation in zip(
            diagnostic_attempts, pending_evaluations, strict=True
        ):
            assert evaluation is not None and evaluation.run_id is not None
            EvaluateChoiceActivityUseCase(
                learning,
                SystemClockProvider(),
                provider,
                _FixedCodeRubricAssessor(),
            ).execute(attempt.id, evaluation.run_id)

        confirmation = _post(
            client, f'{skill_path}/diagnostic/complete', diagnostic_headers
        )
        assert confirmation.status_code == 200, confirmation.text
        assert confirmation.json()['status'] == 'learning'

        completed = _get(client, f'{skill_path}/diagnostic', diagnostic_headers)
        assert completed.status_code == 200, completed.text
        summary = cast('dict[str, Any]', completed.json())
        assert summary['status'] == 'learning'
        assert len(summary['competencies']) == 1
        assert summary['competencies'][0]['competencyId'] is not None
        assert summary['competencies'][0]['progress'] is not None
        assert summary['competencies'][0]['status'] is not None
        assert isinstance(summary['competencies'][0]['coverageComplete'], bool)
        baseline = summary['competencies'][0]['progress']
        competency_id = summary['competencies'][0]['competencyId']
        detail_path = f'{skill_path}/competencies/{competency_id}'
        detail = _get(client, detail_path, headers)
        assert detail.status_code == 200, detail.text
        detail_body = cast('dict[str, Any]', detail.json())
        recommendation = detail_body['adaptive']
        assert recommendation['targetConceptId'] == SEED_ADAPTIVE_CONCEPT_ID
        assert recommendation['activityId'] is not None
        assert summary['initialRecommendation'] is not None
        assert (
            summary['initialRecommendation']['activityId']
            == recommendation['activityId']
        )
        assert (
            summary['initialRecommendation']['targetConceptName']
            == detail_body['adaptive']['targetConceptName']
        )
        activity_id = recommendation['activityId']
        learning_activity_path = f'{detail_path}/activities/{activity_id}'
        learning_activity = _get(client, learning_activity_path, headers)
        assert learning_activity.status_code == 200, learning_activity.text
        learning_activity_data = cast('dict[str, Any]', learning_activity.json())
        assert learning_activity_data['is_diagnostic'] is False
        learning_answers = [
            {'question_key': question['key'], 'selected_option_keys': ['a']}
            for question in learning_activity_data['questions']
        ]
        learning_submission = _post(
            client,
            f'{learning_activity_path}/attempts',
            headers,
            {'submission_key': str(uuid4()), 'answers': learning_answers},
        )
        assert learning_submission.status_code == 201, learning_submission.text
        learning_attempt_id = cast('dict[str, Any]', learning_submission.json())[
            'attempt_id'
        ]
        with learning.transaction() as repositories:
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                learning_attempt_id
            )
            assert evaluation is not None and evaluation.run_id is not None
            learning_run_id = evaluation.run_id
        EvaluateChoiceActivityUseCase(
            learning,
            SystemClockProvider(),
            provider,
            _FixedCodeRubricAssessor(),
        ).execute(learning_attempt_id, learning_run_id)
        learning_result = _get(
            client,
            f'{learning_activity_path}/attempts/{learning_attempt_id}',
            headers,
        )
        assert learning_result.status_code == 200, learning_result.text
        assert cast('dict[str, Any]', learning_result.json())['status'] == 'completed'
        later_summary = _get(client, f'{skill_path}/diagnostic', diagnostic_headers)
        assert later_summary.status_code == 200, later_summary.text
        later_summary_data = cast('dict[str, Any]', later_summary.json())
        assert later_summary_data['competencies'] == summary['competencies']
        assert (
            later_summary_data['initialRecommendation']
            == summary['initialRecommendation']
        )
        with postgres_database.engine.connect() as connection:
            assert (
                connection.scalar(
                    select(func.count()).select_from(ConceptObservationModel)
                )
                == 4
            )
            state = connection.execute(
                select(
                    ConceptStateModel.initial_progress,
                    ConceptStateModel.current_progress,
                ).where(ConceptStateModel.concept_id == SEED_ADAPTIVE_CONCEPT_ID)
            ).one()
            assert state.initial_progress is not None
            assert float(state.initial_progress) == pytest.approx(baseline)


class TestAdaptiveLabSeed:
    def test_should_exercise_two_competencies_and_persist_progress(
        self,
        adaptive_app: FastAPI,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        headers = {'Authorization': 'Bearer test-access-token'}
        seed = build_development_seed()
        activities = {activity.id: activity for activity in seed.activities}
        single_code = activities[SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS[0]]
        multiple_code = activities[SEED_ADAPTIVE_LAB_BOOLEAN_ACTIVITY_IDS[3]]
        assert '```python' in single_code.questions[0].prompt
        assert '```python' in multiple_code.questions[0].prompt
        assert isinstance(multiple_code.questions[0], MultipleSelectionQuestion)
        learning = SqlalchemyLearningDatabase(postgres_database.engine)
        provider = DatabaseCurriculumContentProvider(
            SqlalchemyCurriculumDatabase(postgres_database.engine)
        )

        def disposable_seed_settings(cls: type[SeedSettings]) -> SeedSettings:
            return cls(
                database_url=postgres_database.url,
                server_app_mode='local',
            )

        monkeypatch.setattr(
            SeedSettings,
            'from_environment',
            classmethod(disposable_seed_settings),
        )
        seed_database()

        def submit_and_evaluate(
            client: TestClient,
            skill_path: str,
            competency_id: str,
            activity_id: str,
            *,
            correct: bool,
            diagnostic_run_id: str | None = None,
        ) -> dict[str, object] | None:
            request_headers = (
                headers
                if diagnostic_run_id is None
                else {**headers, 'X-Diagnostic-Run-Id': diagnostic_run_id}
            )
            activity = activities[activity_id]
            path = f'{skill_path}/competencies/{competency_id}/activities/{activity_id}'
            response = _get(client, path, request_headers)
            assert response.status_code == 200, response.text
            wire_questions = cast('dict[str, Any]', response.json())['questions']
            answers: list[dict[str, object]] = []
            for question, wire in zip(activity.questions, wire_questions, strict=True):
                assert wire['prompt'] == question.prompt
                if isinstance(question, JavascriptStdinQuestion):
                    assert wire['kind'] == 'javascript_stdin'
                    answers.append(
                        {
                            'kind': 'javascript_stdin',
                            'question_key': question.key,
                            'files': [
                                {
                                    'path': item['path'],
                                    'content': item['content'],
                                }
                                for item in wire['initial_files']
                                if item['editable']
                            ],
                        }
                    )
                    continue
                assert isinstance(
                    question, (SingleChoiceQuestion, MultipleSelectionQuestion)
                )
                expected_kind = (
                    'multiple_selection'
                    if isinstance(question, MultipleSelectionQuestion)
                    else 'single_choice'
                )
                assert wire['kind'] == expected_kind
                selected_keys = [
                    option.key
                    for option in question.options
                    if option.is_correct is correct
                ]
                answers.append(
                    {
                        'question_key': question.key,
                        'kind': expected_kind,
                        'selected_option_keys': (
                            selected_keys if correct else selected_keys[:1]
                        ),
                    }
                )
            if diagnostic_run_id is not None:
                activity_data = cast('dict[str, Any]', response.json())
                return {
                    'competency_id': competency_id,
                    'activity_id': activity_id,
                    'activity_revision': activity_data['activity_revision'],
                    'answers': answers,
                }
            submission = _post(
                client,
                f'{path}/attempts',
                request_headers,
                {'submission_key': str(uuid4()), 'answers': answers},
            )
            assert submission.status_code == 201, submission.text
            attempt_id = cast('dict[str, Any]', submission.json())['attempt_id']
            with learning.transaction() as repositories:
                evaluation = repositories.activity_evaluations.find_by_attempt_id(
                    attempt_id
                )
                assert evaluation is not None and evaluation.run_id is not None
                run_id = evaluation.run_id
            EvaluateChoiceActivityUseCase(
                learning,
                SystemClockProvider(),
                provider,
                _FixedCodeRubricAssessor(
                    0 if diagnostic_run_id is not None else 100 if correct else 0
                ),
            ).execute(attempt_id, run_id)
            return None

        def submit_diagnostic_batch(
            client: TestClient,
            skill_path: str,
            diagnostic_run_id: str,
        ) -> None:
            diagnostic_headers = {
                **headers,
                'X-Diagnostic-Run-Id': diagnostic_run_id,
            }
            initial_overview = _get(
                client, f'{skill_path}/diagnostic', diagnostic_headers
            )
            assert initial_overview.status_code == 200, initial_overview.text
            activity_sequence = cast(
                'list[dict[str, Any]]',
                cast('dict[str, Any]', initial_overview.json())['activitySequence'],
            )
            assert len(activity_sequence) == 9
            expected_competency_ids = [
                SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID
            ] * 6 + [SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID] * 3
            diagnostic_ids: set[str] = set()
            diagnostic_items: list[dict[str, object]] = []
            for index, sequence_item in enumerate(activity_sequence):
                competency_id = sequence_item['competencyId']
                activity_id = sequence_item['activityId']
                assert competency_id == expected_competency_ids[index]
                assert activity_id not in diagnostic_ids
                diagnostic_ids.add(activity_id)
                diagnostic_item = submit_and_evaluate(
                    client,
                    skill_path,
                    competency_id,
                    activity_id,
                    correct=index in (6, 7),
                    diagnostic_run_id=diagnostic_run_id,
                )
                assert diagnostic_item is not None
                diagnostic_items.append(diagnostic_item)

            diagnostic_submission = _post(
                client,
                f'{skill_path}/diagnostic/submissions',
                diagnostic_headers,
                {'submission_key': str(uuid4()), 'items': diagnostic_items},
            )
            assert diagnostic_submission.status_code == 201, diagnostic_submission.text
            assert diagnostic_submission.json() == {
                'status': 'pending',
                'replayed': False,
            }
            with learning.transaction() as repositories:
                diagnostic_experience = (
                    repositories.skill_experiences.find_by_goal_id_and_skill_id(
                        SEED_ADAPTIVE_LAB_GOAL_ID,
                        SEED_ADAPTIVE_LAB_SKILL_ID,
                    )
                )
                assert diagnostic_experience is not None
                diagnostic_attempts = repositories.activity_attempts.find_many_by_skill_experience_id_and_diagnostic_run_id(
                    diagnostic_experience.id,
                    diagnostic_run_id,
                )
                diagnostic_evaluations = tuple(
                    repositories.activity_evaluations.find_by_attempt_id(attempt.id)
                    for attempt in diagnostic_attempts
                )
            assert len(diagnostic_attempts) == len(diagnostic_items)
            for attempt, evaluation in zip(
                diagnostic_attempts, diagnostic_evaluations, strict=True
            ):
                assert evaluation is not None and evaluation.run_id is not None
                EvaluateChoiceActivityUseCase(
                    learning,
                    SystemClockProvider(),
                    provider,
                    _FixedCodeRubricAssessor(score=0),
                ).execute(attempt.id, evaluation.run_id)

        with TestClient(adaptive_app, raise_server_exceptions=True) as client:
            adaptive_app.state.cache_provider = _UnlimitedCache()
            available = _get(client, '/learning/available-skills', headers)
            assert available.status_code == 200
            skill = next(
                item
                for item in cast('dict[str, Any]', available.json())['skills']
                if item['id'] == SEED_ADAPTIVE_LAB_SKILL_ID
            )
            assert skill['available'] is True
            goal_id = SEED_ADAPTIVE_LAB_GOAL_ID
            goal = _get(client, f'/learning/goals/{goal_id}', headers)
            assert goal.status_code == 200, goal.text
            skill_path = (
                f'/learning/goals/{goal_id}/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
            )
            diagnostic_run_id = str(uuid4())
            started = _post(
                client,
                f'{skill_path}/start',
                headers,
                {'entry_key': diagnostic_run_id},
            )
            assert started.status_code == 200, started.text
            diagnostic_headers = {**headers, 'X-Diagnostic-Run-Id': diagnostic_run_id}
            submit_diagnostic_batch(client, skill_path, diagnostic_run_id)

            confirmation = _post(
                client, f'{skill_path}/diagnostic/complete', diagnostic_headers
            )
            assert confirmation.status_code == 200, confirmation.text
            assert confirmation.json()['status'] in {'learning', 'completed'}

            overview = _get(client, f'{skill_path}/diagnostic', diagnostic_headers)
            assert overview.status_code == 200, overview.text
            summary = cast('dict[str, Any]', overview.json())
            assert summary['status'] == 'learning'
            assert len(summary['competencies']) == 2
            baseline = {
                item['competencyId']: item['progress']
                for item in summary['competencies']
            }
            assert baseline[SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID] == 0
            assert baseline[SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID] is not None
            with postgres_database.engine.connect() as connection:
                assert (
                    connection.scalar(
                        select(func.count()).select_from(ConceptObservationModel)
                    )
                    == 9
                )

            first_detail = _get(
                client,
                f'{skill_path}/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}',
                headers,
            )
            assert first_detail.status_code == 200, first_detail.text
            first_data = cast('dict[str, Any]', first_detail.json())
            assert first_data['adaptive']['targetConceptId'] == (
                SEED_ADAPTIVE_LAB_CONDITIONS_CONCEPT_ID
            )
            assert first_data['adaptive']['materialId'] == (
                SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID
            )
            assert first_data['adaptive']['materialIsOptional'] is True

            practiced, targeted = _practice_until_mastered(
                client,
                skill_path,
                headers,
                submit_and_evaluate,
            )
            assert targeted == {
                SEED_ADAPTIVE_LAB_CONDITIONS_CONCEPT_ID,
                SEED_ADAPTIVE_LAB_BOOLEAN_CONCEPT_ID,
            }
            assert len(practiced) >= 6

            mastered = _get(
                client,
                f'{skill_path}/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}',
                headers,
            )
            assert mastered.status_code == 200, mastered.text
            mastered_data = cast('dict[str, Any]', mastered.json())
            assert mastered_data['status'] == 'mastered'
            assert mastered_data['progress'] >= 85

            later = _get(client, f'{skill_path}/diagnostic', diagnostic_headers)
            assert later.status_code == 200
            later_baseline = {
                item['competencyId']: item['progress']
                for item in cast('dict[str, Any]', later.json())['competencies']
            }
            assert later_baseline == baseline
            next_detail = _get(
                client,
                f'{skill_path}/competencies/{SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID}',
                headers,
            )
            assert next_detail.status_code == 200, next_detail.text
            next_data = cast('dict[str, Any]', next_detail.json())
            assert next_data['availability'] == 'available'
            assert next_data['adaptive']['targetConceptId'] == (
                SEED_ADAPTIVE_LAB_PRIORITY_CONCEPT_ID
            )

        # The explicit local seed can restore the starting point in a disposable DB.
        seed_database()
        with postgres_database.engine.connect() as connection:
            assert (
                connection.scalar(
                    select(func.count()).select_from(ConceptObservationModel)
                )
                == 0
            )
            assert connection.scalar(select(func.count()).select_from(EventModel)) == 0

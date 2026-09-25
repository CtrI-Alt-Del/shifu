"""Persisted HTTP journey for an eligible adaptive Skill in disposable PostgreSQL."""

from collections.abc import Iterator
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
            policy_id = connection.scalar(
                select(SkillExperienceModel.policy_id).where(
                    SkillExperienceModel.goal_id == goal_id
                )
            )
        assert policy_id == 'learning-adaptive-v2'

        started = _post(client, f'{skill_path}/start', headers)
        assert started.status_code == 200, started.text
        visited: list[str] = []
        for expected_difficulty in ('easy', 'medium', 'hard'):
            overview = _get(client, f'{skill_path}/diagnostic', headers)
            assert overview.status_code == 200, overview.text
            data = cast('dict[str, Any]', overview.json())
            assert data['status'] == 'diagnosing'
            assert data['competencies'] == []
            assert data['pendingAttemptId'] is None
            competency_id = data['nextCompetencyId']
            activity_id = data['nextActivityId']
            assert activity_id not in visited
            visited.append(activity_id)
            activity_path = (
                f'{skill_path}/competencies/{competency_id}/activities/{activity_id}'
            )
            activity = _get(client, activity_path, headers)
            assert activity.status_code == 200, activity.text
            activity_data = cast('dict[str, Any]', activity.json())
            assert activity_data['is_diagnostic'] is True
            assert activity_data['difficulty'] == expected_difficulty
            answers = [
                {
                    'question_key': question['key'],
                    'selected_option_keys': ['a'],
                }
                for question in activity_data['questions']
            ]
            submitted = _post(
                client,
                f'{activity_path}/attempts',
                headers,
                {'submission_key': str(uuid4()), 'answers': answers},
            )
            assert submitted.status_code == 201, submitted.text
            submitted_data = cast('dict[str, Any]', submitted.json())
            assert submitted_data['is_diagnostic'] is True
            assert submitted_data['result_url'] == f'{skill_path}/diagnostic'
            attempt_id = submitted_data['attempt_id']
            private_result = _get(
                client, f'{activity_path}/attempts/{attempt_id}', headers
            )
            assert private_result.status_code == 404
            pending = cast(
                'dict[str, Any]',
                _get(client, f'{skill_path}/diagnostic', headers).json(),
            )
            assert pending['pendingAttemptId'] == attempt_id
            assert pending['pendingAttemptStatus'] == 'pending'
            with learning.transaction() as repositories:
                evaluation = repositories.activity_evaluations.find_by_attempt_id(
                    attempt_id
                )
                assert evaluation is not None and evaluation.run_id is not None
                run_id = evaluation.run_id
            EvaluateChoiceActivityUseCase(
                learning, SystemClockProvider(), provider
            ).execute(attempt_id, run_id)

        completed = _get(client, f'{skill_path}/diagnostic', headers)
        assert completed.status_code == 200, completed.text
        summary = cast('dict[str, Any]', completed.json())
        assert summary['status'] == 'learning'
        assert len(summary['competencies']) == 1
        assert summary['competencies'][0]['competencyId'] is not None
        assert summary['competencies'][0]['progress'] is not None
        assert 'status' not in summary['competencies'][0]
        assert 'coverageComplete' not in summary['competencies'][0]
        baseline = summary['competencies'][0]['progress']
        competency_id = summary['competencies'][0]['competencyId']
        detail_path = f'{skill_path}/competencies/{competency_id}'
        detail = _get(client, detail_path, headers)
        assert detail.status_code == 200, detail.text
        recommendation = cast('dict[str, Any]', detail.json())['adaptive']
        assert recommendation['targetConceptId'] == SEED_ADAPTIVE_CONCEPT_ID
        assert recommendation['activityId'] is not None
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
            learning, SystemClockProvider(), provider
        ).execute(learning_attempt_id, learning_run_id)
        learning_result = _get(
            client,
            f'{learning_activity_path}/attempts/{learning_attempt_id}',
            headers,
        )
        assert learning_result.status_code == 200, learning_result.text
        assert cast('dict[str, Any]', learning_result.json())['status'] == 'completed'
        later_summary = _get(client, f'{skill_path}/diagnostic', headers)
        assert later_summary.status_code == 200, later_summary.text
        assert (
            cast('dict[str, Any]', later_summary.json())['competencies'][0]['progress']
            == baseline
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
            assert float(state.initial_progress) == baseline


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
        ) -> None:
            activity = activities[activity_id]
            path = f'{skill_path}/competencies/{competency_id}/activities/{activity_id}'
            response = _get(client, path, headers)
            assert response.status_code == 200, response.text
            wire_questions = cast('dict[str, Any]', response.json())['questions']
            for question, wire in zip(activity.questions, wire_questions, strict=True):
                assert wire['prompt'] == question.prompt
                assert wire['kind'] == (
                    'multiple_selection'
                    if isinstance(question, MultipleSelectionQuestion)
                    else 'single_choice'
                )
            answers: list[dict[str, object]] = []
            for question in activity.questions:
                assert isinstance(
                    question, (SingleChoiceQuestion, MultipleSelectionQuestion)
                )
                selected_keys = [
                    option.key
                    for option in question.options
                    if option.is_correct is correct
                ]
                answers.append(
                    {
                        'question_key': question.key,
                        'selected_option_keys': (
                            selected_keys if correct else selected_keys[:1]
                        ),
                    }
                )
            submission = _post(
                client,
                f'{path}/attempts',
                headers,
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
                learning, SystemClockProvider(), provider
            ).execute(attempt_id, run_id)

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
            started = _post(client, f'{skill_path}/start', headers)
            assert started.status_code == 200, started.text

            diagnostic_ids: list[str] = []
            for index in range(9):
                overview = _get(client, f'{skill_path}/diagnostic', headers)
                assert overview.status_code == 200, overview.text
                data = cast('dict[str, Any]', overview.json())
                competency_id = data['nextCompetencyId']
                activity_id = data['nextActivityId']
                assert competency_id == (
                    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID
                    if index < 6
                    else SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID
                )
                assert activity_id not in diagnostic_ids
                diagnostic_ids.append(activity_id)
                submit_and_evaluate(
                    client,
                    skill_path,
                    competency_id,
                    activity_id,
                    correct=index in (6, 7),
                )

            overview = _get(client, f'{skill_path}/diagnostic', headers)
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

            later = _get(client, f'{skill_path}/diagnostic', headers)
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

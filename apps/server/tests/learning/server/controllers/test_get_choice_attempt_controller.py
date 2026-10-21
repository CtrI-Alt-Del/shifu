from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from shifu.app import FastAPIApp
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.database.sqlalchemy.mappers import ActivityMapper
from shifu.curriculum.core.domain.structures import (
    CodeRubricEvaluationPart,
    ReactQuestion,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.database.sqlalchemy.models import ActivityAttemptModel
from shifu.learning.pipes import LearningPipe
from shifu.learning.core.use_cases import EvaluateChoiceActivityUseCase
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.structures import CodeQuestionAssessmentDecisions
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import (
    AuthenticatedUser,
    CodeCriterionDecision,
    CodeRubricDecisions,
    CurriculumCodeRubricPartSnapshot,
    CurriculumReactQuestionSnapshot,
)
from shifu.shared.core.interfaces import ClockProvider
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS,
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_PROGRESS_ID,
    SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
    SEED_ADAPTIVE_LAB_GOAL_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
    build_development_seed,
)
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture
from tests.learning.server.controllers.react_controller_fixture import (
    ReactControllerFixture,
)

if TYPE_CHECKING:
    from httpx import Response


_NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)
_LEARNING_ACTIVITY_ID = SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS[4]


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=SEED_ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
        )


class _FixedClockProvider(ClockProvider):
    def now(self) -> datetime:
        return _NOW


class _NoopBroker:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    seed = build_development_seed()
    curriculum_database = SqlalchemyCurriculumDatabase(postgres_database.engine)
    with curriculum_database.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
        repositories.competencies.add_many(list(seed.competencies))
        repositories.concepts.add_many(list(seed.concepts))
        repositories.materials.add_many(list(seed.materials))
        repositories.activities.add_many(list(seed.activities))
        repositories.curriculum_sequences.add_many(list(seed.curriculum_sequences))
    learning_database = SqlalchemyLearningDatabase(postgres_database.engine)
    with learning_database.transaction() as repositories:
        repositories.goals.add_many(list(seed.goals))
        repositories.skill_experiences.add_many(list(seed.skill_experiences))
        repositories.competency_progresses.add_many(list(seed.competency_progresses))
        repositories.activity_attempts.add_many(list(seed.activity_attempts))
        repositories.activity_evaluations.add_many(list(seed.activity_evaluations))
        experience = repositories.skill_experiences.find_by_id(
            SEED_ADAPTIVE_LAB_EXPERIENCE_ID
        )
        assert experience is not None
        experience.status = SkillExperienceStatus.LEARNING
        repositories.skill_experiences.update(experience)
        progress = repositories.competency_progresses.find_by_id(
            SEED_ADAPTIVE_LAB_CONDITIONS_PROGRESS_ID
        )
        assert progress is not None
        progress.content_released = True
        repositories.competency_progresses.update(progress)

    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _TestAuthenticationProvider()
    application.state.inngest_broker = _NoopBroker()
    application.dependency_overrides[LearningPipe.get_clock_provider] = lambda: (
        _FixedClockProvider()
    )
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestGetChoiceAttemptController:
    @pytest.mark.parametrize(
        'legacy_answer',
        (
            {'question_key': 'q1', 'source_code': "console.log('Olá')"},
            {'question_key': 'q1', 'selected_option_key': 'a'},
        ),
        ids=('source-code', 'choice'),
    )
    def test_attempt_without_frozen_snapshot_remains_private_for_legacy_answers(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
        legacy_answer: dict[str, str],
    ) -> None:
        created = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=_submission_body(),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        assert created.status_code == 201, created.json()
        attempt_id = cast('str', created.json()['attempt_id'])
        with Session(postgres_database.engine) as session, session.begin():
            model = session.get(ActivityAttemptModel, attempt_id)
            assert model is not None
            model.grading_snapshot = None
            model.answers = [legacy_answer]

        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _attempt_path(attempt_id),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 404, response.json()
        assert response.json()['code'] == 'not_found'

    def test_react_history_freezes_project_prompt_policy_and_rubric_after_curriculum_edit(
        self,
        client: TestClient,
        application: FastAPI,
        postgres_database: PostgresDatabase,
    ) -> None:
        activity = ReactControllerFixture.activity()
        curriculum = SqlalchemyCurriculumDatabase(postgres_database.engine)
        with curriculum.transaction() as repositories:
            repositories.activities.add_many([activity])
        headers = {'Authorization': 'Bearer test-access-token'}
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                ReactControllerFixture.activity_path(), headers=headers
            ),
        )
        assert detail.status_code == 200, detail.json()
        revision = cast('str', detail.json()['activity_revision'])
        created = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                f'{ReactControllerFixture.activity_path()}/attempts',
                json=ReactControllerFixture.submission(revision),
                headers=headers,
            ),
        )
        assert created.status_code == 201, created.json()
        attempt_id = cast('str', created.json()['attempt_id'])
        path = f'{ReactControllerFixture.activity_path()}/attempts/{attempt_id}'

        question = activity.questions[2]
        assert isinstance(question, ReactQuestion)
        activity.questions = (
            *activity.questions[:2],
            replace(
                question,
                prompt='Novo enunciado curricular',
                initial_files=(
                    replace(question.initial_files[0], content='// New curriculum'),
                    replace(question.initial_files[1], content='<main>New HTML</main>'),
                ),
                additional_file_policy=None,
            ),
        )
        part = activity.evaluation_rule.parts[2]
        assert isinstance(part, CodeRubricEvaluationPart)
        criterion = part.criteria[0]
        activity.evaluation_rule = replace(
            activity.evaluation_rule,
            parts=(
                *activity.evaluation_rule.parts[:2],
                replace(
                    part,
                    criteria=(
                        replace(
                            criterion,
                            fixed_comments=tuple(
                                replace(comment, text='New curricular comment')
                                for comment in criterion.fixed_comments
                            ),
                        ),
                    ),
                ),
            ),
        )
        # The repository has no content-edit operation; replace this fixture row
        # through its production mapper to simulate a later curricular revision.
        with Session(postgres_database.engine) as session, session.begin():
            session.merge(ActivityMapper.to_model(activity))

        changed_detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                ReactControllerFixture.activity_path(), headers=headers
            ),
        )
        assert changed_detail.status_code == 200, changed_detail.json()
        assert changed_detail.json()['activity_revision'] != revision
        assert (
            changed_detail.json()['questions'][2]['prompt']
            == 'Novo enunciado curricular'
        )
        assert (
            changed_detail.json()['questions'][2].get('additional_file_policy') is None
        )

        pending = cast(
            'Response',
            client.get(path, headers=headers),  # pyright: ignore[reportUnknownMemberType]
        )
        assert pending.status_code == 200, pending.json()
        assert pending.json()['status'] == 'pending'
        pending_react = pending.json()['questions'][0]
        assert pending_react['kind'] == 'react'
        assert pending_react['prompt'] == ReactControllerFixture.PROMPT
        assert (
            pending_react['submitted_files'] == ReactControllerFixture.composed_files()
        )

        database = SqlalchemyLearningDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
        assert attempt is not None and attempt.grading_snapshot is not None
        snapshot = attempt.grading_snapshot
        assert snapshot.revision == revision
        frozen_question = snapshot.questions[2]
        assert isinstance(frozen_question, CurriculumReactQuestionSnapshot)
        assert (
            frozen_question.initial_files[0].content
            == ReactControllerFixture.INITIAL_SOURCE
        )
        assert (
            frozen_question.initial_files[1].content
            == ReactControllerFixture.FIXED_HTML
        )
        assert frozen_question.additional_file_policy is not None
        frozen_part = snapshot.parts[2]
        assert isinstance(frozen_part, CurriculumCodeRubricPartSnapshot)
        assert frozen_part.criteria[0].fixed_comments[3].text == 'Fixed comment 75'
        assert evaluation is not None and evaluation.run_id is not None

        EvaluateChoiceActivityUseCase(
            database,
            _FixedClockProvider(),
            application.state.curriculum_content_provider,
        ).execute(
            attempt_id,
            evaluation.run_id,
            (
                CodeQuestionAssessmentDecisions(
                    question_key='q3',
                    decisions=CodeRubricDecisions(
                        criterion_levels=(
                            CodeCriterionDecision(key='correctness', level=75),
                        ),
                        concept_levels=(),
                    ),
                ),
            ),
        )

        completed = cast(
            'Response',
            client.get(path, headers=headers),  # pyright: ignore[reportUnknownMemberType]
        )
        assert completed.status_code == 200, completed.json()
        body = completed.json()
        assert body['status'] == 'completed'
        assert body['score'] == '90.00'
        react = body['questions'][2]
        assert react['question_key'] == 'q3'
        assert react['kind'] == 'react'
        assert react['prompt'] == ReactControllerFixture.PROMPT
        assert react['submitted_files'] == ReactControllerFixture.composed_files()
        assert react['criterion_results'] == [
            {
                'key': 'correctness',
                'weight_percentage': 100,
                'level': 75,
                'comment_id': 'comment-75',
                'comment': 'Fixed comment 75',
            }
        ]
        assert 'New curricular' not in str(body)
        assert 'New HTML' not in str(body)

    def test_completed_attempt_includes_question_results_and_safe_disclosure(
        self,
        client: TestClient,
        application: FastAPI,
    ) -> None:
        body = _submission_body()
        answers = cast('list[dict[str, object]]', body['answers'])
        answers[0]['selected_option_keys'] = ['b']
        answers[1]['selected_option_keys'] = ['b']
        created = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=body,
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert created.status_code == 201, created.json()
        attempt_id = cast('str', created.json()['attempt_id'])
        database: SqlalchemyLearningDatabase = application.state.learning_database
        with database.transaction() as repositories:
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
            assert evaluation is not None
            run_id = evaluation.run_id
            assert run_id is not None
        EvaluateChoiceActivityUseCase(
            database,
            _FixedClockProvider(),
            application.state.curriculum_content_provider,
        ).execute(attempt_id, run_id)

        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _attempt_path(attempt_id),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200, response.json()
        payload = response.json()

        assert payload['status'] == 'completed'
        questions = cast('list[dict[str, object]]', payload['questions'])

        assert [question['question_key'] for question in questions] == [
            'q1',
            'q2',
            'q3',
        ]
        assert [question['selected_option_keys'] for question in questions] == [
            ['b'],
            ['b'],
            ['a'],
        ]
        assert [
            question['disclosed_correct_option_keys'] for question in questions
        ] == [
            [],
            ['b'],
            ['a'],
        ]

    def test_stale_pending_attempt_becomes_failed_without_result_disclosure(
        self,
        client: TestClient,
        application: FastAPI,
    ) -> None:
        created = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=_submission_body(),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert created.status_code == 201, created.json()
        attempt_id = cast('str', created.json()['attempt_id'])
        database: SqlalchemyLearningDatabase = application.state.learning_database
        with database.transaction() as repositories:
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
            assert evaluation is not None
            evaluation.started_at = _NOW - timedelta(minutes=6)
            repositories.activity_evaluations.update(evaluation)

        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _attempt_path(attempt_id),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200
        assert response.json()['status'] == 'failed'
        assert response.json()['retry_allowed'] is True
        assert response.json()['failure_message']
        assert 'score' not in response.json()
        assert 'questions' not in response.json()

    def test_attempt_for_another_hierarchy_is_private_absence(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _attempt_path('01SHF000000000000000000099'),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 404


def _attempts_path() -> str:
    return (
        f'/learning/goals/{SEED_ADAPTIVE_LAB_GOAL_ID}/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
        f'/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}'
        f'/activities/{_LEARNING_ACTIVITY_ID}/attempts'
    )


def _attempt_path(attempt_id: str) -> str:
    return f'{_attempts_path()}/{attempt_id}'


def _submission_body() -> dict[str, object]:
    return {
        'submission_key': '75e29c3d-8bc2-4e4d-9103-cc747a170012',
        'answers': [
            {
                'question_key': question_key,
                'selected_option_keys': ['b' if question_key == 'q2' else 'a'],
            }
            for question_key in ('q1', 'q2', 'q3')
        ],
    }

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast
from uuid import UUID

import pytest
from fastapi import Request
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from shifu.app import FastAPIApp
from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    ChoiceOption,
    CodeInconclusiveComment,
    CodeRubricComment,
    CodeRubricCriterion,
    CodeRubricEvaluationPart,
    CorrectnessEvaluationPart,
    EvaluationRule,
    JavascriptInitialFile,
    JavascriptStdinQuestion,
    SingleChoiceQuestion,
)
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.learning.core.domain.structures import CodeAnswer
from shifu.learning.core.domain.enums import (
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.database.sqlalchemy.models import ActivityAttemptModel
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import (
    AuthenticatedUser,
    CurriculumReactQuestionSnapshot,
)
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS,
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_GOAL_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
    build_development_seed,
)
from shifu.shared.rest.pipes.telemetry_pipe import TelemetryPipe
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture
from tests.learning.server.controllers.react_controller_fixture import (
    ReactControllerFixture,
)

if TYPE_CHECKING:
    from httpx import Response


_SUBMISSION_KEY = '75e29c3d-8bc2-4e4d-9103-cc747a170012'
_ACTIVITY_ID = SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS[3]


class _TestAuthenticationProvider:
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


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    seed = build_development_seed()
    learning_started_at = datetime(2026, 1, 1, tzinfo=UTC)
    for experience in seed.skill_experiences:
        if experience.status is not SkillExperienceStatus.NOT_STARTED:
            continue
        experience.start_diagnosis(learning_started_at)
        experience.start_learning(learning_started_at)
    for progress in seed.competency_progresses:
        progress.content_released = True
        progress.initial_progress = Decimal('55')
        progress.current_progress = Decimal('55')
        progress.status = CompetencyProgressStatus.DEVELOPING
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

    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _TestAuthenticationProvider()
    application.state.inngest_broker = _NoopBroker()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestSubmitChoiceActivityController:
    @pytest.mark.parametrize(
        'answer',
        (
            {'kind': 'react', 'question_key': 'q3'},
            {
                'kind': 'react',
                'question_key': 'q3',
                'files': [],
                'selected_option_keys': ['a'],
            },
            {'kind': 'single_choice', 'question_key': 'q1'},
            {
                'kind': 'single_choice',
                'question_key': 'q1',
                'files': [],
                'selected_option_keys': ['a'],
            },
        ),
        ids=(
            'code-without-files',
            'mixed-code-shape',
            'choice-without-options',
            'mixed-choice-shape',
        ),
    )
    def test_should_reject_malformed_answer_shape_before_persistence(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
        answer: dict[str, object],
    ) -> None:
        before = ReactControllerFixture.write_counts(postgres_database)

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                f'{ReactControllerFixture.activity_path()}/attempts',
                headers={'Authorization': 'Bearer test-access-token'},
                json={
                    'submission_key': 'e9aa7b85-c95b-4319-b98e-5ca293c09f61',
                    'answers': [answer],
                },
            ),
        )

        assert response.status_code == 422, response.json()
        assert ReactControllerFixture.write_counts(postgres_database) == before

    @pytest.mark.parametrize('with_policy', [True, False])
    def test_react_submission_round_trips_files_policy_and_same_key_replay(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
        with_policy: bool,
    ) -> None:
        def no_request_id(_request: Request) -> None:
            return None

        monkeypatch.setattr(
            TelemetryPipe,
            'get_request_id',
            staticmethod(no_request_id),
        )
        curriculum = SqlalchemyCurriculumDatabase(postgres_database.engine)
        with curriculum.transaction() as repositories:
            repositories.activities.add_many(
                [ReactControllerFixture.activity(with_policy=with_policy)]
            )
        headers = {'Authorization': 'Bearer test-access-token'}
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                ReactControllerFixture.activity_path(), headers=headers
            ),
        )
        assert detail.status_code == 200, detail.json()
        revision = cast('str', detail.json()['activity_revision'])
        body = ReactControllerFixture.submission(revision)
        answers = cast('list[dict[str, object]]', body['answers'])
        if not with_policy:
            answers[2]['files'] = ReactControllerFixture.answer_files()[:1]
        before = ReactControllerFixture.write_counts(postgres_database)

        created = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                f'{ReactControllerFixture.activity_path()}/attempts',
                json=body,
                headers=headers,
            ),
        )

        assert created.status_code == 201, created.json()
        attempt_id = cast('str', created.json()['attempt_id'])
        assert created.json()['status'] == 'pending'
        assert created.json()['result_url'].endswith(f'/attempts/{attempt_id}')
        database = SqlalchemyLearningDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
        assert attempt is not None
        snapshot = attempt.grading_snapshot
        assert snapshot is not None
        assert snapshot.revision == revision
        question = snapshot.questions[2]
        assert isinstance(question, CurriculumReactQuestionSnapshot)
        assert question.kind == 'react'
        assert question.prompt == ReactControllerFixture.PROMPT
        assert (
            question.initial_files[0].content == ReactControllerFixture.INITIAL_SOURCE
        )
        assert question.initial_files[1].content == ReactControllerFixture.FIXED_HTML
        assert (question.additional_file_policy is not None) is with_policy
        if question.additional_file_policy is not None:
            assert question.additional_file_policy.allowed_directories == (
                'src/components',
            )
            assert question.additional_file_policy.allowed_extensions == ('.jsx', '.js')
            assert question.additional_file_policy.max_files == 2
        answer = attempt.answers[2]
        assert isinstance(answer, CodeAnswer)
        assert answer.kind == 'react'
        assert [
            {'path': file.path, 'content': file.content} for file in answer.files
        ] == (
            ReactControllerFixture.answer_files()
            if with_policy
            else ReactControllerFixture.answer_files()[:1]
        )
        assert evaluation is not None and evaluation.status.value == 'pending'
        assert evaluation.run_id is not None
        after_created = ReactControllerFixture.write_counts(postgres_database)
        assert after_created == (before[0] + 1, before[1] + 1, before[2], before[3] + 1)

        replay = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                f'{ReactControllerFixture.activity_path()}/attempts',
                json=body,
                headers=headers,
            ),
        )

        assert replay.status_code == 200, replay.json()
        assert replay.json() == created.json()
        assert ReactControllerFixture.write_counts(postgres_database) == after_created

    def test_react_submit_uses_configured_assessment_size_limit(
        self,
        client: TestClient,
        application: FastAPI,
        postgres_database: PostgresDatabase,
    ) -> None:
        curriculum = SqlalchemyCurriculumDatabase(postgres_database.engine)
        with curriculum.transaction() as repositories:
            repositories.activities.add_many([ReactControllerFixture.activity()])
        application.dependency_overrides[
            LearningPipe.get_max_code_assessment_input_bytes
        ] = lambda: 512 * 1024
        headers = {'Authorization': 'Bearer test-access-token'}
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                ReactControllerFixture.activity_path(), headers=headers
            ),
        )
        assert detail.status_code == 200, detail.json()
        body = ReactControllerFixture.submission(
            cast('str', detail.json()['activity_revision'])
        )
        answers = cast('list[dict[str, object]]', body['answers'])
        large_source = 'x' * (300 * 1024)
        answers[2]['files'] = [{'path': 'src/App.jsx', 'content': large_source}]

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                f'{ReactControllerFixture.activity_path()}/attempts',
                json=body,
                headers=headers,
            ),
        )

        assert response.status_code == 201, response.json()
        database = SqlalchemyLearningDatabase(postgres_database.engine)
        with database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(
                cast('str', response.json()['attempt_id'])
            )
        assert attempt is not None
        answer = attempt.answers[2]
        assert isinstance(answer, CodeAnswer)
        assert answer.files[0].content == large_source

    @pytest.mark.parametrize('with_policy', [True, False])
    def test_react_submit_rejects_forbidden_extra_files_without_persistence(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
        with_policy: bool,
    ) -> None:
        curriculum = SqlalchemyCurriculumDatabase(postgres_database.engine)
        with curriculum.transaction() as repositories:
            repositories.activities.add_many(
                [ReactControllerFixture.activity(with_policy=with_policy)]
            )
        headers = {'Authorization': 'Bearer test-access-token'}
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                ReactControllerFixture.activity_path(), headers=headers
            ),
        )
        assert detail.status_code == 200, detail.json()
        body = ReactControllerFixture.submission(
            cast('str', detail.json()['activity_revision'])
        )
        answers = cast('list[dict[str, object]]', body['answers'])
        files = cast('list[dict[str, str]]', answers[2]['files'])
        if with_policy:
            files[1]['path'] = 'src/unauthorized.jsx'
        before = ReactControllerFixture.write_counts(postgres_database)

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                f'{ReactControllerFixture.activity_path()}/attempts',
                json=body,
                headers=headers,
            ),
        )

        assert response.status_code == 400, response.json()
        assert response.json()['code'] == 'validation_error'
        assert ReactControllerFixture.write_counts(postgres_database) == before

    def test_creates_attempt_and_same_key_replay_returns_the_same_attempt(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        first = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=_body(client),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert first.status_code == 201, first.json()
        attempt_id = cast('str', first.json()['attempt_id'])
        learning_database = SqlalchemyLearningDatabase(postgres_database.engine)
        with learning_database.transaction() as repositories:
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
            assert evaluation is not None
            evaluation.complete(Decimal('100'), datetime.now(UTC), ())
            repositories.activity_evaluations.update(evaluation)
        replay = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=_body(client),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        changed_answer = _body(client)
        changed_answers = cast('list[dict[str, object]]', changed_answer['answers'])
        changed_answers[0]['selected_option_keys'] = ['b']
        key_mismatch = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=changed_answer,
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert first.status_code == 201, first.json()
        assert first.json()['status'] == 'pending'
        assert first.json()['result_url'].endswith(
            f'/attempts/{first.json()["attempt_id"]}'
        )
        assert replay.status_code == 200
        assert replay.json() == first.json()
        assert key_mismatch.status_code == 409
        assert key_mismatch.json()['code'] == 'conflict'
        with postgres_database.engine.connect() as connection:
            assert (
                connection.scalar(
                    select(func.count())
                    .select_from(ActivityAttemptModel)
                    .where(ActivityAttemptModel.submission_key == _SUBMISSION_KEY)
                )
                == 1
            )

    def test_rejects_semantically_invalid_answers_and_malformed_body(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        invalid_answer = _body(client)
        invalid_answers = cast('list[dict[str, object]]', invalid_answer['answers'])
        invalid_answers[0]['selected_option_keys'] = ['not-an-option']
        with postgres_database.engine.connect() as connection:
            attempts_before = connection.scalar(
                select(func.count()).select_from(ActivityAttemptModel)
            )
        invalid = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json=invalid_answer,
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        malformed = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(),
                json={'submission_key': 'not-a-uuid', 'answers': []},
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert invalid.status_code == 400
        assert invalid.json()['code'] == 'validation_error'
        assert malformed.status_code == 422
        with postgres_database.engine.connect() as connection:
            assert (
                connection.scalar(
                    select(func.count()).select_from(ActivityAttemptModel)
                )
                == attempts_before
            )

    def test_mixed_submission_persists_the_saved_snapshot_and_code_files(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        activity = _mixed_activity()
        curriculum_database = SqlalchemyCurriculumDatabase(postgres_database.engine)
        with curriculum_database.transaction() as repositories:
            repositories.activities.add_many([activity])

        headers = {'Authorization': 'Bearer test-access-token'}
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _activity_path(activity.id),
                headers=headers,
            ),
        )

        assert detail.status_code == 200, detail.json()
        revision = cast('str', detail.json()['activity_revision'])
        body: dict[str, object] = {
            'submission_key': '7c3c84ce-7185-43bc-8b75-c9b250000091',
            'activity_revision': revision,
            'answers': [
                {
                    'kind': 'single_choice',
                    'question_key': 'q1',
                    'selected_option_keys': ['a'],
                },
                {
                    'kind': 'single_choice',
                    'question_key': 'q2',
                    'selected_option_keys': ['a'],
                },
                {
                    'kind': 'javascript_stdin',
                    'question_key': 'q3',
                    'files': [{'path': 'src/main.js', 'content': 'console.log(7)'}],
                },
            ],
        }

        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(activity.id),
                json=body,
                headers=headers,
            ),
        )

        assert response.status_code == 201, response.json()
        attempt_id = cast('str', response.json()['attempt_id'])
        learning_database = SqlalchemyLearningDatabase(postgres_database.engine)
        with learning_database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )

        assert attempt is not None
        assert attempt.grading_snapshot is not None
        assert attempt.grading_snapshot.id == activity.id
        code_answer = attempt.answers[2]

        assert isinstance(code_answer, CodeAnswer)
        assert code_answer.files[0].content == 'console.log(7)'
        assert evaluation is not None
        assert evaluation.status.value == 'pending'
        assert evaluation.run_id is not None

        replay = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                _attempts_path(activity.id),
                json=body,
                headers=headers,
            ),
        )

        assert replay.status_code == 200
        assert replay.json()['attempt_id'] == attempt_id


def _attempts_path(
    activity_id: str = _ACTIVITY_ID,
) -> str:
    return (
        f'/learning/goals/{SEED_ADAPTIVE_LAB_GOAL_ID}'
        f'/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
        f'/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}'
        f'/activities/{activity_id}/attempts'
    )


def _body(client: TestClient) -> dict[str, object]:
    detail = cast(
        'Response',
        client.get(  # pyright: ignore[reportUnknownMemberType]
            _activity_path(_ACTIVITY_ID),
            headers={'Authorization': 'Bearer test-access-token'},
        ),
    )
    assert detail.status_code == 200, detail.json()
    questions = cast('list[dict[str, object]]', detail.json()['questions'])
    answers = [
        {
            'kind': 'single_choice',
            'question_key': question['key'],
            'selected_option_keys': [
                cast('dict[str, str]', cast('list[object]', question['options'])[0])[
                    'key'
                ]
            ],
        }
        for question in questions
    ]
    return {
        'submission_key': str(UUID(_SUBMISSION_KEY)),
        'activity_revision': detail.json()['activity_revision'],
        'answers': answers,
    }


def _activity_path(activity_id: str) -> str:
    return _attempts_path(activity_id).removesuffix('/attempts')


def _mixed_activity() -> Activity:
    questions = tuple(
        SingleChoiceQuestion(
            key=f'q{index}',
            prompt='Escolha',
            options=(
                ChoiceOption(key='a', text='A', is_correct=True),
                ChoiceOption(key='b', text='B', is_correct=False),
            ),
            correct_explanation='Certo',
            incorrect_explanation='Errado',
        )
        for index in (1, 2)
    )
    code = JavascriptStdinQuestion(
        key='q3',
        prompt='Leia stdin',
        initial_files=(
            JavascriptInitialFile(
                path='src/main.js', content='console.log(1)', editable=True
            ),
        ),
        entrypoint='src/main.js',
        fixed_dependencies=(),
        permitted_commands=(),
        concept_criteria=(),
    )
    criterion = CodeRubricCriterion(
        key='correctness',
        name='Correção',
        description='Saída',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CodeRubricComment(
                id=f'comment-{level}', level=level, text=f'Fixed comment {level}'
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CodeInconclusiveComment(id='unknown', text='Inconclusivo'),
    )
    return Activity.create(
        id='01SHF000000000000000000091',
        competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.EASY,
        title='Atividade mista',
        objective='Aprender',
        questions=(*questions, code),
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(question_key='q1', weight_percentage=30),
                CorrectnessEvaluationPart(question_key='q2', weight_percentage=30),
                CodeRubricEvaluationPart(
                    question_key='q3', weight_percentage=40, criteria=(criterion,)
                ),
            )
        ),
    )

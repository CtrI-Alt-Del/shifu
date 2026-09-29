from collections.abc import Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.curriculum.database.logic_programming_seed import (
    LOGIC_CLASSIFY_ACTIVITY_ID,
    LOGIC_DECISIONS_COMPETENCY_ID,
    LOGIC_SKILL_ID,
    build_logic_programming_seed,
)
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
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
    JavascriptDependency,
    JavascriptInitialFile,
    JavascriptStdinQuestion,
    SingleChoiceQuestion,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS,
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_PROGRESS_ID,
    SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
    SEED_ADAPTIVE_LAB_GOAL_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
    SEED_GOAL_ID,
    SEED_LOGIC_EXPERIENCE_ID,
    build_development_seed,
)
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

if TYPE_CHECKING:
    from httpx import Response


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
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestGetChoiceActivityController:
    def test_seeded_logic_diagnostic_has_progress_for_each_competency(self) -> None:
        seed = build_development_seed()
        logic_competency_ids = {
            item.id for item in seed.competencies if item.skill_id == LOGIC_SKILL_ID
        }
        progress_ids = {
            item.competency_id
            for item in seed.competency_progresses
            if item.skill_experience_id == SEED_LOGIC_EXPERIENCE_ID
        }
        assert progress_ids == logic_competency_ids

    def test_seeded_classification_code_question_exposes_zero_and_two_concepts(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        _release_logic_decisions(postgres_database)
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                f'/learning/goals/{SEED_GOAL_ID}/skills/{LOGIC_SKILL_ID}'
                f'/competencies/{LOGIC_DECISIONS_COMPETENCY_ID}'
                f'/activities/{LOGIC_CLASSIFY_ACTIVITY_ID}',
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body['activity_id'] == LOGIC_CLASSIFY_ACTIVITY_ID
        assert body['title'] == 'Classificar um número'
        assert body['difficulty'] == 'easy'
        assert body['can_submit'] is True
        assert 3 <= len(body['questions']) <= 5
        choice_questions = [
            question
            for question in body['questions']
            if question['kind'] == 'single_choice'
        ]
        assert len(choice_questions) == 3
        assert all(len(question['options']) == 4 for question in choice_questions)
        assert '```javascript\nconst numero = 5;' in choice_questions[1]['prompt']
        assert 'else if (numero < 0)' in choice_questions[1]['prompt']
        code_questions = [
            question
            for question in body['questions']
            if question['kind'] == 'javascript_stdin'
        ]
        assert len(code_questions) == 1
        code = code_questions[0]
        assert code['editable_paths']
        assert code['entrypoint'] in code['editable_paths']
        assert code['permitted_commands']
        assert 'classificarNumero' in str(code['initial_files'])
        assert 'return ""' not in str(code['initial_files'])
        instruction = f'{code["prompt"]} {code["initial_files"]}'
        for expected in ('positivo', 'negativo', 'zero', '0'):
            assert expected in instruction
        assert code['criteria']
        assert [criterion['key'] for criterion in code['criteria']] == [
            'positive_comparison',
            'positive_return',
            'negative_return',
            'zero_return',
        ]
        assert [criterion['weight_percentage'] for criterion in code['criteria']] == [
            25,
            25,
            25,
            25,
        ]
        logic = build_logic_programming_seed()
        concept_ids = {
            concept.name: concept.id
            for concept in logic.concepts
            if concept.competency_id == LOGIC_DECISIONS_COMPETENCY_ID
        }
        activity = next(
            item for item in logic.activities if item.id == LOGIC_CLASSIFY_ACTIVITY_ID
        )
        code_rubric = next(
            part
            for part in activity.evaluation_rule.parts
            if isinstance(part, CodeRubricEvaluationPart)
        )
        negative_criterion = next(
            criterion
            for criterion in code_rubric.criteria
            if criterion.key == 'negative_return'
        )
        assert 'numero >= 0' in negative_criterion.description
        assert 'incondicional' in negative_criterion.description
        code_question = next(
            question
            for question in activity.questions
            if isinstance(question, JavascriptStdinQuestion)
        )
        assert {
            criterion.concept_id for criterion in code_question.concept_criteria
        } == {
            concept_ids['Comparações e limites'],
            concept_ids['Decisão condicional'],
        }
        assert not {
            criterion.concept_id
            for question in activity.questions
            for criterion in getattr(question, 'concept_criteria', ())
        }.intersection(
            {
                concept_ids['E lógico'],
                concept_ids['OU lógico'],
                concept_ids['NÃO lógico'],
            }
        )

        detail_response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                f'/learning/goals/{SEED_GOAL_ID}/skills/{LOGIC_SKILL_ID}'
                f'/competencies/{LOGIC_DECISIONS_COMPETENCY_ID}',
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        assert detail_response.status_code == 200, detail_response.text
        detail = detail_response.json()
        assert detail['availability'] == 'available'
        classification = next(
            item for item in detail['items'] if item['id'] == LOGIC_CLASSIFY_ACTIVITY_ID
        )
        assert {concept['name'] for concept in classification['concepts']} == {
            'Comparações e limites',
            'Decisão condicional',
        }

    def test_returns_safe_mixed_project_and_exact_fixed_dependencies(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        mixed_id = '01SHF000000000000000000090'
        choice = tuple(
            SingleChoiceQuestion(
                key=f'q{index}',
                prompt='Escolha',
                options=(ChoiceOption(key='a', text='A', is_correct=True),),
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
                JavascriptInitialFile(
                    path='src/helper.js', content='export const x = 1', editable=False
                ),
            ),
            entrypoint='src/main.js',
            fixed_dependencies=(
                JavascriptDependency(name='left-pad', version='1.3.0'),
            ),
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
                    id=f'comment-{level}', level=level, text=f'Private {level}'
                )
                for level in (0, 25, 50, 75, 100)
            ),
            inconclusive_comment=CodeInconclusiveComment(
                id='unknown', text='Private unknown'
            ),
        )
        activity = Activity.create(
            id=mixed_id,
            competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='Atividade mista',
            objective='Aprender',
            questions=(*choice, code),
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
        curriculum_database = SqlalchemyCurriculumDatabase(postgres_database.engine)
        with curriculum_database.transaction() as repositories:
            repositories.activities.add_many([activity])

        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _activity_path(activity_id=mixed_id),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200, response.json()
        body = response.json()
        assert body['activity_revision']
        assert [item['kind'] for item in body['questions']] == [
            'single_choice',
            'single_choice',
            'javascript_stdin',
        ]
        assert body['questions'][2]['fixed_dependencies'] == [
            {'name': 'left-pad', 'version': '1.3.0'}
        ]
        assert body['questions'][2]['editable_paths'] == ['src/main.js']
        assert body['questions'][2]['criteria'] == [
            {'key': 'correctness', 'name': 'Correção', 'weight_percentage': 100}
        ]
        assert 'Private' not in str(body)

    def test_returns_ordered_safe_questions_without_grading_data(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _activity_path(),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert response.status_code == 200, response.json()
        body = response.json()
        assert body['activity_id'] == _LEARNING_ACTIVITY_ID
        assert body['difficulty'] == 'easy'
        assert [question['key'] for question in body['questions']] == [
            'q1',
            'q2',
            'q3',
        ]
        assert body['can_submit'] is True
        assert body['latest_attempt_id'] is None
        assert body['unresolved_attempt_id'] is None
        assert set(body['questions'][0]['options'][0]) == {'key', 'text'}
        assert 'is_correct' not in str(body)
        assert 'explanation' not in str(body)

    def test_requires_authentication_and_hides_private_absence(
        self,
        client: TestClient,
    ) -> None:
        unauthenticated = cast(
            'Response',
            client.get(_activity_path()),  # pyright: ignore[reportUnknownMemberType]
        )
        private_absence = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _activity_path(goal_id='01SHF000000000000000000099'),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        assert unauthenticated.status_code == 401
        assert private_absence.status_code == 404
        assert private_absence.json() == {
            'code': 'not_found',
            'message': 'Recurso não encontrado.',
        }

    def test_returns_latest_and_unresolved_attempt_ids_for_return_navigation(
        self,
        client: TestClient,
    ) -> None:
        submitted = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                f'{_activity_path()}/attempts',
                json={
                    'submission_key': '75e29c3d-8bc2-4e4d-9103-cc747a170012',
                    'answers': [
                        {
                            'question_key': question_key,
                            'selected_option_keys': ['a'],
                        }
                        for question_key in ('q1', 'q2', 'q3')
                    ],
                },
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        detail = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _activity_path(),
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )

        attempt_id = cast('str', submitted.json()['attempt_id'])
        assert submitted.status_code == 201
        assert detail.status_code == 200
        assert detail.json()['latest_attempt_id'] == attempt_id
        assert detail.json()['unresolved_attempt_id'] == attempt_id
        assert detail.json()['can_submit'] is False


def _activity_path(
    *,
    goal_id: str = SEED_ADAPTIVE_LAB_GOAL_ID,
    activity_id: str = _LEARNING_ACTIVITY_ID,
) -> str:
    return (
        f'/learning/goals/{goal_id}/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
        f'/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}'
        f'/activities/{activity_id}'
    )


def _release_logic_decisions(database: PostgresDatabase) -> None:
    learning = SqlalchemyLearningDatabase(database.engine)
    with learning.transaction() as repositories:
        experience = repositories.skill_experiences.find_by_id(SEED_LOGIC_EXPERIENCE_ID)
        assert experience is not None
        experience.status = SkillExperienceStatus.LEARNING
        repositories.skill_experiences.update(experience)
        progress = repositories.competency_progresses.find_by_skill_experience_id_and_competency_id(
            SEED_LOGIC_EXPERIENCE_ID, LOGIC_DECISIONS_COMPETENCY_ID
        )
        assert progress is not None
        progress.content_released = True
        progress.updated_at = datetime.now(UTC)
        repositories.competency_progresses.update(progress)

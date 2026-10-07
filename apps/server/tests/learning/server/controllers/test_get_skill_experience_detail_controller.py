from collections.abc import Iterator
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from shifu.app import FastAPIApp
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    CodeRubricEvaluationPart,
    JavascriptStdinQuestion,
    MaterialSequenceItem,
)
from shifu.curriculum.database.logic_programming_seed import (
    LOGIC_SKILL_ID,
    build_logic_programming_seed,
)
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers.curriculum_content_provider import (
    DatabaseCurriculumContentProvider,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_GOAL_ID,
    SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
    SEED_GOAL_ID,
    SEED_SKILL_PYTHON_ID,
    build_development_seed,
)
from shifu.shared.database.sqlalchemy.models import EventModel
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

if TYPE_CHECKING:
    from httpx import Response

ABSENT_ID = '01SHF000000000000000000999'


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=SEED_ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
        )


class _OtherAccountAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id='01SHF000000000000000000777',
            display_name='Outra Pessoa',
            time_zone='America/Sao_Paulo',
        )


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    _seed_application(postgres_database)
    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _TestAuthenticationProvider()
    application.state.learning_database = SqlalchemyLearningDatabase(
        postgres_database.engine
    )
    application.state.curriculum_content_provider = DatabaseCurriculumContentProvider(
        SqlalchemyCurriculumDatabase(postgres_database.engine)
    )
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


class TestGetSkillExperienceDetailController:
    def test_logic_seed_has_complete_concept_and_activity_coverage(
        self,
        client: TestClient,
    ) -> None:
        response = _get(client, goal_id=SEED_GOAL_ID, skill_id=LOGIC_SKILL_ID)

        assert response.status_code == 200, response.text

        bundle = build_logic_programming_seed()
        competencies = sorted(bundle.competencies, key=lambda item: item.position)
        concepts = sorted(
            bundle.concepts,
            key=lambda item: (
                next(
                    competency.position
                    for competency in competencies
                    if competency.id == item.competency_id
                ),
                item.position,
            ),
        )

        assert len(concepts) == 15
        assert len({concept.id for concept in concepts}) == 15
        assert [concept.name for concept in concepts] == [
            'Ordem de execução',
            'Entrada e saída',
            'Rastreamento de valores',
            'Atribuição',
            'Atualização de valores',
            'Expressões aritméticas',
            'Comparações e limites',
            'Decisão condicional',
            'E lógico',
            'OU lógico',
            'NÃO lógico',
            'Repetição por quantidade',
            'Condição de parada',
            'Dividir em etapas',
            'Parâmetros e retorno',
        ]
        ordinal = {concept.id: index for index, concept in enumerate(concepts)}
        for concept in concepts:
            assert all(
                prerequisite in ordinal and ordinal[prerequisite] < ordinal[concept.id]
                for prerequisite in concept.prerequisite_ids
            )

        for competency in competencies:
            sequence = next(
                sequence
                for sequence in bundle.curriculum_sequences
                if sequence.competency_id == competency.id
            )
            assert any(
                isinstance(item, MaterialSequenceItem) for item in sequence.items
            )
            assert any(
                activity.competency_id == competency.id
                and any(
                    isinstance(question, JavascriptStdinQuestion)
                    for question in activity.questions
                )
                for activity in bundle.activities
                if activity.activity_type is ActivityType.LEARNING
            )

        for activity in bundle.activities:
            if activity.activity_type is ActivityType.LEARNING:
                assert 3 <= len(activity.questions) <= 5
            for question in activity.questions:
                if not isinstance(question, JavascriptStdinQuestion):
                    continue
                part = next(
                    item
                    for item in activity.evaluation_rule.parts
                    if item.question_key == question.key
                )
                assert isinstance(part, CodeRubricEvaluationPart)
                for criterion in part.criteria:
                    assert tuple(
                        sorted(comment.level for comment in criterion.fixed_comments)
                    ) == (0, 25, 50, 75, 100)
                    assert criterion.inconclusive_comment is not None

        for concept in concepts:
            for difficulty in ActivityDifficulty:
                covering = [
                    activity
                    for activity in bundle.activities
                    if activity.difficulty is difficulty
                    and any(
                        criterion.concept_id == concept.id
                        for question in activity.questions
                        for criterion in getattr(question, 'concept_criteria', ())
                    )
                ]
                assert any(
                    activity.activity_type is ActivityType.DIAGNOSTIC
                    for activity in covering
                ), (concept.name, difficulty)
                assert (
                    len(
                        {
                            activity.id
                            for activity in covering
                            if activity.activity_type is ActivityType.LEARNING
                        }
                    )
                    >= 2
                ), (concept.name, difficulty)

    def test_seeded_logic_skill_starts_fresh_with_five_ordered_competencies(
        self,
        client: TestClient,
    ) -> None:
        goal_response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                f'/learning/goals/{SEED_GOAL_ID}',
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        )
        response = _get(client, goal_id=SEED_GOAL_ID, skill_id=LOGIC_SKILL_ID)

        assert goal_response.status_code == 200, goal_response.text
        assert any(
            skill['skillId'] == LOGIC_SKILL_ID
            for skill in goal_response.json()['skills']
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert body['goalId'] == SEED_GOAL_ID
        assert body['skillId'] == LOGIC_SKILL_ID
        assert body['skillName'] == 'Lógica de programação'
        assert body['skillStatus'] == 'not-started'
        assert body['overallResult'] is None
        assert [item['competencyName'] for item in body['competencies']] == [
            'Sequência de instruções',
            'Variáveis e expressões',
            'Decisões',
            'Repetição',
            'Decomposição em funções',
        ]
        assert [item['position'] for item in body['competencies']] == [1, 2, 3, 4, 5]
        assert all(item['progress'] is None for item in body['competencies'])

    def test_owner_reads_the_experience_without_writing_events(
        self,
        client: TestClient,
        postgres_database: PostgresDatabase,
    ) -> None:
        before_events = _event_count(postgres_database)

        response = _get(client, skill_id=SEED_ADAPTIVE_LAB_SKILL_ID)

        assert response.status_code == 200
        body = response.json()

        assert body['goalId'] == SEED_ADAPTIVE_LAB_GOAL_ID
        assert body['skillId'] == SEED_ADAPTIVE_LAB_SKILL_ID
        assert body['skillName'] == 'Laboratório de decisões adaptativas'
        assert body['skillStatus'] == 'not-started'
        assert 'skill_name' not in body
        assert _event_count(postgres_database) == before_events

    def test_lists_every_competency_in_curricular_order_with_its_state(
        self,
        client: TestClient,
    ) -> None:
        body = _get(client, skill_id=SEED_ADAPTIVE_LAB_SKILL_ID).json()

        competencies = body['competencies']

        assert [item['position'] for item in competencies] == sorted(
            item['position'] for item in competencies
        )
        assert {item['competencyId'] for item in competencies} == {
            SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID,
        }
        assert all(
            item['availability'] in {'available', 'unavailable'}
            for item in competencies
        )

    def test_focus_is_the_first_competency_that_is_not_mastered(
        self,
        client: TestClient,
    ) -> None:
        body = _get(client, skill_id=SEED_ADAPTIVE_LAB_SKILL_ID).json()

        focused = [item for item in body['competencies'] if item['isFocus']]

        assert len(focused) <= 1
        assert body['focusCompetencyId'] == (
            focused[0]['competencyId'] if focused else None
        )
        if focused:
            first_unmastered = next(
                item for item in body['competencies'] if item['status'] != 'mastered'
            )
            assert focused[0]['competencyId'] == first_unmastered['competencyId']

    def test_overall_result_averages_every_competency(
        self,
        client: TestClient,
    ) -> None:
        body = _get(client, skill_id=SEED_ADAPTIVE_LAB_SKILL_ID).json()

        progresses = [
            item['progress']
            for item in body['competencies']
            if item['progress'] is not None
        ]
        expected = sum(progresses) / len(progresses) if progresses else None
        if expected is None:
            assert body['overallResult'] is None
        else:
            assert body['overallResult'] == pytest.approx(expected)

    def test_recommendation_matches_the_focus_competency_endpoint(
        self,
        client: TestClient,
    ) -> None:
        skill_body = _get(client, skill_id=SEED_ADAPTIVE_LAB_SKILL_ID).json()
        focus_id = skill_body['focusCompetencyId']
        if focus_id is None:
            assert skill_body['recommendation'] is None
            return
        competency_body = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                f'/learning/goals/{SEED_ADAPTIVE_LAB_GOAL_ID}'
                f'/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
                f'/competencies/{focus_id}',
                headers={'Authorization': 'Bearer test-access-token'},
            ),
        ).json()

        recommendation = skill_body['recommendation']

        assert recommendation == competency_body.get('recommendation')
        if recommendation is None:
            return
        for field in ('competencyId', 'activityId', 'difficulty', 'type'):
            assert recommendation[field] == competency_body['recommendation'][field]

    def test_removed_incompatible_skill_is_a_private_absence(
        self,
        client: TestClient,
    ) -> None:
        response = _get(client, skill_id=SEED_SKILL_PYTHON_ID)

        assert response.status_code == 404

    def test_skill_outside_the_goal_is_a_private_absence(
        self,
        client: TestClient,
    ) -> None:
        response = _get(client, skill_id=ABSENT_ID)

        assert response.status_code == 404
        assert response.json() == {
            'code': 'not_found',
            'message': 'Recurso não encontrado.',
        }

    def test_goal_of_another_account_is_a_private_absence(
        self,
        application: FastAPI,
    ) -> None:
        application.state.authentication_provider = (
            _OtherAccountAuthenticationProvider()
        )

        with TestClient(application, raise_server_exceptions=False) as client:
            response = _get(client, skill_id=SEED_ADAPTIVE_LAB_SKILL_ID)

        assert response.status_code == 404
        assert response.json() == {
            'code': 'not_found',
            'message': 'Recurso não encontrado.',
        }

    def test_missing_bearer_is_unauthorized(self, client: TestClient) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                _path(SEED_ADAPTIVE_LAB_GOAL_ID, SEED_ADAPTIVE_LAB_SKILL_ID)
            ),
        )

        assert response.status_code == 401


def _get(
    client: TestClient,
    *,
    skill_id: str,
    goal_id: str = SEED_ADAPTIVE_LAB_GOAL_ID,
) -> 'Response':
    return cast(
        'Response',
        client.get(  # pyright: ignore[reportUnknownMemberType]
            _path(goal_id, skill_id),
            headers={'Authorization': 'Bearer test-access-token'},
        ),
    )


def _path(goal_id: str, skill_id: str) -> str:
    return f'/learning/goals/{goal_id}/skills/{skill_id}'


def _event_count(database: PostgresDatabase) -> int:
    with database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(EventModel)) or 0


def _seed_application(database: PostgresDatabase) -> None:
    seed = build_development_seed()
    curriculum_database = SqlalchemyCurriculumDatabase(database.engine)
    with curriculum_database.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
        repositories.competencies.add_many(list(seed.competencies))
        repositories.concepts.add_many(list(seed.concepts))
        repositories.materials.add_many(list(seed.materials))
        repositories.activities.add_many(list(seed.activities))
        repositories.curriculum_sequences.add_many(list(seed.curriculum_sequences))

    learning_database = SqlalchemyLearningDatabase(database.engine)
    with learning_database.transaction() as repositories:
        repositories.goals.add_many(list(seed.goals))
        repositories.skill_experiences.add_many(list(seed.skill_experiences))
        repositories.competency_progresses.add_many(list(seed.competency_progresses))
        repositories.activity_attempts.add_many(list(seed.activity_attempts))
        repositories.activity_evaluations.add_many(list(seed.activity_evaluations))

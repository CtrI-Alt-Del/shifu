from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
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
from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    CompetencyProgress,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityDifficulty as LearningDifficulty,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures import (
    CompetencyCompletionSummary,
    ConceptCompletionSummary,
    ConceptObservation,
    SkillCompletionSummary,
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
COMPLETED_GOAL_ID = '01SHF000000000000000000901'
COMPLETED_EXPERIENCE_ID = '01SHF000000000000000000902'
OTHER_ACCOUNT_ID = '01SHF000000000000000000777'
STARTED_AT = datetime(2026, 9, 2, 23, 30, tzinfo=UTC)
COMPLETED_AT = datetime(2026, 9, 13, 2, 0, tzinfo=UTC)
MASTERED_AT = (
    datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
    datetime(2026, 9, 6, 1, 0, tzinfo=UTC),
    datetime(2026, 9, 8, 15, 0, tzinfo=UTC),
    datetime(2026, 9, 10, 2, 30, tzinfo=UTC),
    datetime(2026, 9, 13, 2, 0, tzinfo=UTC),
)


class _TestAuthenticationProvider:
    def __init__(self, time_zone: str | None = 'America/Sao_Paulo') -> None:
        self._time_zone = time_zone

    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=SEED_ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone=self._time_zone,
        )


class _OtherAccountAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=OTHER_ACCOUNT_ID,
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


@pytest.fixture
def completed_goal(application: FastAPI, postgres_database: PostgresDatabase) -> None:
    _seed_completed_goal(postgres_database)


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

    def test_seeded_logic_skill_exposes_learning_progress_across_ordered_competencies(
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
        assert body['skillStatus'] == 'learning'
        assert body['overallResult'] == pytest.approx(100.0)
        assert [item['competencyName'] for item in body['competencies']] == [
            'Sequência de instruções',
            'Variáveis e expressões',
            'Decisões',
            'Repetição',
            'Decomposição em funções',
        ]
        assert [item['position'] for item in body['competencies']] == [1, 2, 3, 4, 5]
        assert [item['progress'] for item in body['competencies']] == [100.0] * 5

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

    def test_completed_skill_returns_the_exact_completion_in_the_account_time_zone(
        self,
        client: TestClient,
        completed_goal: None,
        postgres_database: PostgresDatabase,
    ) -> None:
        before_events = _event_count(postgres_database)

        response = _get(client, goal_id=COMPLETED_GOAL_ID, skill_id=LOGIC_SKILL_ID)

        assert response.status_code == 200, response.text
        body = response.json()

        assert body['skillStatus'] == 'completed'
        assert body['completion'] == _expected_completion(
            started_on='2026-09-02',
            completed_on='2026-09-12',
            duration_days=10,
            mastered_on=(
                '2026-09-04',
                '2026-09-05',
                '2026-09-08',
                '2026-09-09',
                '2026-09-12',
            ),
        )
        assert _event_count(postgres_database) == before_events

    def test_completed_skill_follows_the_utc_fallback_without_an_account_time_zone(
        self,
        application: FastAPI,
        completed_goal: None,
    ) -> None:
        application.state.authentication_provider = _TestAuthenticationProvider(None)

        with TestClient(application, raise_server_exceptions=False) as client:
            response = _get(client, goal_id=COMPLETED_GOAL_ID, skill_id=LOGIC_SKILL_ID)

        assert response.status_code == 200, response.text
        assert response.json()['completion'] == _expected_completion(
            started_on='2026-09-02',
            completed_on='2026-09-13',
            duration_days=11,
            mastered_on=(
                '2026-09-04',
                '2026-09-06',
                '2026-09-08',
                '2026-09-10',
                '2026-09-13',
            ),
        )

    def test_learning_experience_of_the_same_skill_has_no_completion(
        self,
        client: TestClient,
        completed_goal: None,
    ) -> None:
        learning = _get(client, goal_id=SEED_GOAL_ID, skill_id=LOGIC_SKILL_ID)
        completed = _get(client, goal_id=COMPLETED_GOAL_ID, skill_id=LOGIC_SKILL_ID)

        assert learning.status_code == 200, learning.text
        assert learning.json()['skillStatus'] == 'learning'
        assert learning.json()['completion'] is None
        assert completed.status_code == 200, completed.text
        assert completed.json()['skillStatus'] == 'completed'
        assert completed.json()['completion'] is not None

    def test_not_started_experience_has_no_completion(
        self,
        client: TestClient,
    ) -> None:
        body = _get(client, skill_id=SEED_ADAPTIVE_LAB_SKILL_ID).json()

        assert 'completion' in body
        assert body['completion'] is None

    def test_completed_goal_of_another_account_is_a_private_absence(
        self,
        application: FastAPI,
        completed_goal: None,
    ) -> None:
        application.state.authentication_provider = (
            _OtherAccountAuthenticationProvider()
        )

        with TestClient(application, raise_server_exceptions=False) as client:
            response = _get(client, goal_id=COMPLETED_GOAL_ID, skill_id=LOGIC_SKILL_ID)

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


def _id(number: int) -> str:
    return f'01SHF{number:021d}'


def _expected_completion(
    *,
    started_on: str,
    completed_on: str,
    duration_days: int,
    mastered_on: tuple[str, str, str, str, str],
) -> dict[str, object]:
    competencies = sorted(
        build_logic_programming_seed().competencies, key=lambda item: item.position
    )
    initial = (40.0, None, 60.0, 70.0, 50.0)
    coverage = ('complete', 'unknown', 'partial', 'complete', 'partial')
    final = (90.0, 80.0, 85.0, 95.0, 88.0)
    return {
        'startedOn': started_on,
        'completedOn': completed_on,
        'durationDays': duration_days,
        'completedByDiagnosis': False,
        'learningActivityCount': 2,
        'learningAttemptCount': 3,
        'initialResult': 55.0,
        'initialResultCoverage': 'partial',
        'finalResult': 90.0,
        'competencies': [
            {
                'competencyId': competency.id,
                'competencyName': competency.name,
                'position': competency.position,
                'initialProgress': initial[index],
                'initialCoverage': coverage[index],
                'finalProgress': final[index],
                'masteredOn': mastered_on[index],
            }
            for index, competency in enumerate(competencies)
        ],
        'review': {'attemptCount': 3, 'latestScore': 85.0},
    }


def _seed_completed_goal(database: PostgresDatabase) -> None:
    """Persist a completed Logic experience in a second Goal of the seed account."""
    bundle = build_logic_programming_seed()
    competencies = sorted(bundle.competencies, key=lambda item: item.position)
    concepts_by_competency = {
        competency.id: sorted(
            (item for item in bundle.concepts if item.competency_id == competency.id),
            key=lambda item: item.position,
        )
        for competency in competencies
    }

    def stored_concepts(
        competency_id: str,
        difficulties: tuple[LearningDifficulty, ...],
    ) -> tuple[ConceptCompletionSummary, ...]:
        return tuple(
            ConceptCompletionSummary(
                concept_id=concept.id,
                initial_progress=Decimal('50'),
                final_progress=Decimal('90'),
                initial_observed_difficulties=difficulties,
                final_observed_difficulties=tuple(LearningDifficulty),
            )
            for concept in concepts_by_competency[competency_id]
        )

    stored = (
        CompetencyCompletionSummary(
            competency_id=competencies[0].id,
            initial_progress=Decimal('40'),
            final_progress=Decimal('90'),
            concepts=stored_concepts(competencies[0].id, tuple(LearningDifficulty)),
        ),
        CompetencyCompletionSummary(
            competency_id=competencies[1].id,
            initial_progress=None,
            final_progress=Decimal('80'),
        ),
        CompetencyCompletionSummary(
            competency_id=competencies[2].id,
            initial_progress=Decimal('60'),
            final_progress=Decimal('85'),
            concepts=stored_concepts(
                competencies[2].id,
                (LearningDifficulty.EASY, LearningDifficulty.MEDIUM),
            ),
        ),
        CompetencyCompletionSummary(
            competency_id=competencies[3].id,
            initial_progress=Decimal('70'),
            final_progress=Decimal('95'),
        ),
        CompetencyCompletionSummary(
            competency_id=competencies[4].id,
            initial_progress=Decimal('50'),
            final_progress=Decimal('88'),
        ),
    )
    goal = GoalFaker.fake(
        id=COMPLETED_GOAL_ID,
        account_id=SEED_ACCOUNT_ID,
        title='Carreira em dados',
    )
    experience = SkillExperienceFaker.fake(
        id=COMPLETED_EXPERIENCE_ID,
        goal_id=COMPLETED_GOAL_ID,
        skill_id=LOGIC_SKILL_ID,
        status=SkillExperienceStatus.COMPLETED,
        started_at=STARTED_AT,
        completed_at=COMPLETED_AT,
        completion_summary=SkillCompletionSummary(
            competencies=stored,
            initial_progress=None,
            final_progress=Decimal('90'),
            started_at=STARTED_AT,
            completed_at=COMPLETED_AT,
        ),
    )
    progresses = [
        CompetencyProgress(
            id=_id(910 + index),
            skill_experience_id=COMPLETED_EXPERIENCE_ID,
            competency_id=competency.id,
            content_released=True,
            created_at=STARTED_AT,
            updated_at=COMPLETED_AT,
            initial_progress=Decimal('20'),
            current_progress=Decimal('90'),
            status=CompetencyProgressStatus.MASTERED,
            mastered_at=MASTERED_AT[index],
            hard_activity_score=Decimal('90'),
        )
        for index, competency in enumerate(competencies)
    ]

    def attempt(
        number: int,
        kind: ActivityAttemptKind,
        competency_id: str,
        activity_number: int,
        minute: int,
    ) -> ActivityAttempt:
        return ActivityAttempt(
            id=_id(920 + number),
            skill_experience_id=COMPLETED_EXPERIENCE_ID,
            competency_id=competency_id,
            activity_id=_id(950 + activity_number),
            kind=kind,
            answers=(),
            submitted_at=datetime(2026, 9, 3, 12, minute, tzinfo=UTC),
        )

    first_id = competencies[0].id
    diagnostic = [
        attempt(index, ActivityAttemptKind.DIAGNOSTIC, competencies[3].id, index, index)
        for index in range(3)
    ]
    learning = [
        attempt(3, ActivityAttemptKind.LEARNING, first_id, 10, 10),
        attempt(4, ActivityAttemptKind.LEARNING, first_id, 10, 11),
        attempt(5, ActivityAttemptKind.LEARNING, first_id, 11, 12),
    ]
    review = [
        attempt(6, ActivityAttemptKind.REVIEW, first_id, 10, 20),
        attempt(7, ActivityAttemptKind.REVIEW, first_id, 10, 21),
        attempt(8, ActivityAttemptKind.REVIEW, first_id, 11, 22),
    ]

    def evaluation(
        number: int,
        item: ActivityAttempt,
        status: ActivityEvaluationStatus,
        score: Decimal | None,
        minute: int,
    ) -> ActivityEvaluation:
        return ActivityEvaluation(
            id=_id(940 + number),
            attempt_id=item.id,
            status=status,
            parts=(),
            started_at=item.submitted_at,
            score=score,
            completed_at=(
                datetime(2026, 9, 14, 12, minute, tzinfo=UTC)
                if status is ActivityEvaluationStatus.COMPLETED
                else None
            ),
        )

    evaluations = [
        *(
            evaluation(
                index, item, ActivityEvaluationStatus.COMPLETED, Decimal('80'), 1
            )
            for index, item in enumerate(learning)
        ),
        evaluation(3, review[0], ActivityEvaluationStatus.COMPLETED, Decimal('60'), 5),
        evaluation(4, review[1], ActivityEvaluationStatus.COMPLETED, Decimal('85'), 6),
        evaluation(5, review[2], ActivityEvaluationStatus.PENDING, None, 0),
    ]
    observations = tuple(
        ConceptObservation(
            attempt_id=item.id,
            activity_id=item.activity_id,
            concept_id=concept.id,
            difficulty=difficulty,
            first_submitted_at=item.submitted_at,
            submitted_at=item.submitted_at,
            completed_at=item.submitted_at,
            question_scores=(Decimal('80'),),
            diagnostic=True,
        )
        for item, difficulty in zip(diagnostic, LearningDifficulty, strict=True)
        for concept in concepts_by_competency[competencies[3].id]
    )

    learning_database = SqlalchemyLearningDatabase(database.engine)
    with learning_database.transaction() as repositories:
        repositories.goals.add(goal)
        repositories.skill_experiences.add_many([experience])
        repositories.competency_progresses.add_many(progresses)
        repositories.activity_attempts.add_many([*diagnostic, *learning, *review])
        repositories.activity_evaluations.add_many(evaluations)
        repositories.concept_observations.add_many(
            COMPLETED_EXPERIENCE_ID, competencies[3].id, observations
        )

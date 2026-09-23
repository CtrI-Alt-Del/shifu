import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from shifu.app import FastAPIApp
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from shifu.shared.testing.database import create_test_engine


@pytest.fixture
def test_engine() -> Engine:
    return create_test_engine()


@pytest.fixture
def client(test_engine: Engine) -> TestClient:
    app = FastAPIApp.register(database_engine=test_engine)
    return TestClient(app)


@pytest.fixture
def setup_data(test_engine: Engine):
    id_provider = SystemIdentifierProvider()
    learning_db = SqlalchemyLearningDatabase(engine=test_engine, id_provider=id_provider)
    curriculum_db = SqlalchemyCurriculumDatabase(engine=test_engine)

    goal_id = None
    skill_id = None
    foundation_id = None

    with learning_db.transaction() as learning_repos:
        goal_id = id_provider.provide()
        from shifu.learning.core.domain.entities import Goal
        goal = Goal.create(
            id=goal_id,
            account_id='test-account',
            title='Test Goal',
            description='Test goal description',
        )
        learning_repos.goals.add(goal)

    with curriculum_db.transaction() as curriculum_repos:
        foundation_id = id_provider.provide()
        skill_id = id_provider.provide()

        from shifu.curriculum.core.domain.entities import Skill, SkillFoundation
        foundation = Skill(
            id=foundation_id,
            name='JavaScript',
            description='Learn JavaScript',
        )
        skill = Skill(
            id=skill_id,
            name='React',
            description='Learn React fundamentals',
        )
        curriculum_repos.skills.add_many([foundation, skill])

        foundation_link = SkillFoundation(
            skill_id=skill_id,
            foundation_skill_id=foundation_id,
        )
        curriculum_repos.skill_foundations.add_many([foundation_link])

    return {
        'goal_id': goal_id,
        'skill_id': skill_id,
        'foundation_id': foundation_id,
    }


def test_add_skill_to_goal_success(client: TestClient, setup_data: dict):
    goal_id = setup_data['goal_id']
    skill_id = setup_data['skill_id']

    response = client.post(
        f'/learning/goals/{goal_id}/skills',
        json={'skill_id': skill_id, 'foundation_skill_ids': []},
    )
    assert response.status_code == 201
    data = response.json()
    assert 'created' in data
    assert len(data['created']) == 1
    assert data['created'][0]['skill_id'] == skill_id
    assert data['created'][0]['status'] == 'not-started'


def test_add_skill_with_foundations(client: TestClient, setup_data: dict):
    goal_id = setup_data['goal_id']
    skill_id = setup_data['skill_id']
    foundation_id = setup_data['foundation_id']

    response = client.post(
        f'/learning/goals/{goal_id}/skills',
        json={'skill_id': skill_id, 'foundation_skill_ids': [foundation_id]},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data['created']) == 2
    skill_experience_ids = {exp['skill_id'] for exp in data['created']}
    assert skill_id in skill_experience_ids
    assert foundation_id in skill_experience_ids


def test_add_skill_goal_not_found(client: TestClient, setup_data: dict):
    skill_id = setup_data['skill_id']
    response = client.post(
        '/learning/goals/nonexistent/skills',
        json={'skill_id': skill_id, 'foundation_skill_ids': []},
    )
    assert response.status_code == 404
    assert response.json()['code'] == 'goal_not_found'


def test_add_skill_already_exists(
    client: TestClient, setup_data: dict, test_engine: Engine
):
    goal_id = setup_data['goal_id']
    skill_id = setup_data['skill_id']
    id_provider = SystemIdentifierProvider()
    learning_db = SqlalchemyLearningDatabase(engine=test_engine, id_provider=id_provider)

    with learning_db.transaction() as repos:
        from shifu.learning.core.domain.entities import SkillExperience
        from shifu.learning.core.domain.enums import SkillExperienceStatus
        from datetime import datetime

        exp = SkillExperience.create(
            id=id_provider.provide(),
            goal_id=goal_id,
            skill_id=skill_id,
            inclusion_reason=None,
            status=SkillExperienceStatus.NOT_STARTED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        repos.skill_experiences.add(exp)

    client_instance = TestClient(FastAPIApp.register(database_engine=test_engine))
    response = client_instance.post(
        f'/learning/goals/{goal_id}/skills',
        json={'skill_id': skill_id, 'foundation_skill_ids': []},
    )
    assert response.status_code == 409
    assert response.json()['code'] == 'skill_already_added'


def test_add_skill_invalid_foundation(client: TestClient, setup_data: dict):
    goal_id = setup_data['goal_id']
    skill_id = setup_data['skill_id']

    response = client.post(
        f'/learning/goals/{goal_id}/skills',
        json={'skill_id': skill_id, 'foundation_skill_ids': ['invalid-id']},
    )
    assert response.status_code == 400
    assert response.json()['code'] == 'invalid_goal'

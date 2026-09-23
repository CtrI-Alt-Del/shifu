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
        skill_id = id_provider.provide()
        from shifu.curriculum.core.domain.entities import Skill
        skill = Skill(
            id=skill_id,
            name='React',
            description='Learn React fundamentals',
        )
        curriculum_repos.skills.add_many([skill])

    return {
        'goal_id': goal_id,
        'skill_id': skill_id,
    }


def test_search_skill_catalog_empty_query(client: TestClient, setup_data: dict):
    goal_id = setup_data['goal_id']
    response = client.get(f'/learning/goals/{goal_id}/skills/catalog')
    assert response.status_code == 200
    data = response.json()
    assert 'items' in data
    assert 'next_cursor' in data
    assert isinstance(data['items'], list)


def test_search_skill_catalog_with_query(client: TestClient, setup_data: dict):
    goal_id = setup_data['goal_id']
    response = client.get(
        f'/learning/goals/{goal_id}/skills/catalog?query=React'
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data['items']) > 0
    assert data['items'][0]['name'] == 'React'


def test_search_skill_catalog_goal_not_found(client: TestClient):
    response = client.get('/learning/goals/nonexistent/skills/catalog')
    assert response.status_code == 404
    assert response.json()['code'] == 'goal_not_found'


def test_skill_catalog_response_structure(client: TestClient, setup_data: dict):
    goal_id = setup_data['goal_id']
    response = client.get(f'/learning/goals/{goal_id}/skills/catalog')
    assert response.status_code == 200
    data = response.json()

    assert 'items' in data
    assert 'next_cursor' in data

    if data['items']:
        skill = data['items'][0]
        assert 'id' in skill
        assert 'name' in skill
        assert 'description' in skill
        assert 'already_in_goal' in skill
        assert 'skill_experience_id' in skill
        assert 'foundations' in skill

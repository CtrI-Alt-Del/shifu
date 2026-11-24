"""Seeded practical preparation Activity and application for practice draft HTTP tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from shifu.app import FastAPIApp
from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    CorrectnessEvaluationPart,
    EvaluationRule,
)
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.fakers.curriculum.structures import PracticalPreparationQuestionFaker
from shifu.fakers.identity.entities.account_faker import AccountFaker
from shifu.identity.database.sqlalchemy.identity_database import (
    SqlalchemyIdentityDatabase,
)
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.database.sqlalchemy.models import (
    PracticeDraftModel,
    PracticePhotoModel,
)
from shifu.learning.pipes import LearningPipe
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_PROGRESS_ID,
    SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
    SEED_ADAPTIVE_LAB_GOAL_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
    build_development_seed,
)
from tests.fixtures.fill_blanks_activity_fixture import FillBlanksActivityFixture
from tests.fixtures.practice_photo_storage_fixture import PracticePhotoStorageStub

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi import FastAPI

    from tests.fixtures.postgres_fixture import PostgresDatabase
    from tests.fixtures.redis_fixture import RedisFixture

OWNER_TOKEN = 'test-access-token'
OTHER_TOKEN = 'other-access-token'
OTHER_ACCOUNT_ID = '01SHF000000000000000009999'
AUTH_HEADERS = {'Authorization': f'Bearer {OWNER_TOKEN}'}
OTHER_HEADERS = {'Authorization': f'Bearer {OTHER_TOKEN}'}


class _AuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        accounts = {OWNER_TOKEN: SEED_ACCOUNT_ID, OTHER_TOKEN: OTHER_ACCOUNT_ID}
        if access_token not in accounts:
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=accounts[access_token],
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
            session_id=f'practice-draft-{access_token}',
            token_access_version=1,
            account_access_version=1,
        )


class _NoopBroker:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class PracticeDraftFixture:
    ACTIVITY_ID: ClassVar[str] = '01SHF000000000000000000300'

    @staticmethod
    def activity() -> Activity:
        question = PracticalPreparationQuestionFaker.fake(
            concept_criteria=(
                PracticalPreparationQuestionFaker.concept_criterion(
                    FillBlanksActivityFixture.FIRST_CONCEPT_ID
                ),
            )
        )
        return Activity.create(
            id=PracticeDraftFixture.ACTIVITY_ID,
            competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='Legumes salteados',
            objective='Preparar legumes salteados',
            questions=(question,),
            evaluation_rule=EvaluationRule(
                parts=(
                    CorrectnessEvaluationPart(
                        question_key=question.key, weight_percentage=100
                    ),
                )
            ),
        )

    @staticmethod
    def draft_path(
        *,
        goal_id: str = SEED_ADAPTIVE_LAB_GOAL_ID,
        activity_id: str = ACTIVITY_ID,
    ) -> str:
        return (
            f'/learning/goals/{goal_id}'
            f'/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
            f'/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}'
            f'/activities/{activity_id}/practice-draft'
        )

    @staticmethod
    def counts(database: PostgresDatabase) -> tuple[int, int]:
        with database.engine.connect() as connection:
            return (
                connection.scalar(select(func.count()).select_from(PracticeDraftModel))
                or 0,
                connection.scalar(select(func.count()).select_from(PracticePhotoModel))
                or 0,
            )


@dataclass(frozen=True)
class PracticeDraftClient:
    client: TestClient
    storage: PracticePhotoStorageStub
    database: PostgresDatabase


@pytest.fixture
def practice_application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[tuple[FastAPI, PracticePhotoStorageStub]]:
    del redis_fixture
    seed = build_development_seed()
    with SqlalchemyIdentityDatabase(postgres_database.engine).transaction() as repos:
        for account in seed.accounts:
            if repos.accounts.find_by_id(account.id) is None:
                repos.accounts.add(account)
        if repos.accounts.find_by_id(OTHER_ACCOUNT_ID) is None:
            repos.accounts.add(AccountFaker.fake(id=OTHER_ACCOUNT_ID, access_version=1))
    with SqlalchemyCurriculumDatabase(postgres_database.engine).transaction() as repos:
        repos.skills.add_many(list(seed.skills))
        repos.skill_foundations.add_many(list(seed.skill_foundations))
        repos.competencies.add_many(list(seed.competencies))
        repos.concepts.add_many(list(seed.concepts))
        repos.materials.add_many(list(seed.materials))
        repos.activities.add_many([*seed.activities, PracticeDraftFixture.activity()])
        repos.curriculum_sequences.add_many(list(seed.curriculum_sequences))
    with SqlalchemyLearningDatabase(postgres_database.engine).transaction() as repos:
        repos.goals.add_many(list(seed.goals))
        repos.skill_experiences.add_many(list(seed.skill_experiences))
        repos.competency_progresses.add_many(list(seed.competency_progresses))
        repos.activity_attempts.add_many(list(seed.activity_attempts))
        repos.activity_evaluations.add_many(list(seed.activity_evaluations))
        experience = repos.skill_experiences.find_by_id(SEED_ADAPTIVE_LAB_EXPERIENCE_ID)
        assert experience is not None
        experience.status = SkillExperienceStatus.LEARNING
        repos.skill_experiences.update(experience)
        progress = repos.competency_progresses.find_by_id(
            SEED_ADAPTIVE_LAB_CONDITIONS_PROGRESS_ID
        )
        assert progress is not None
        progress.content_released = True
        repos.competency_progresses.update(progress)

    storage = PracticePhotoStorageStub()
    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _AuthenticationProvider()
    application.state.inngest_broker = _NoopBroker()
    application.dependency_overrides[
        LearningPipe.get_practice_photo_storage_provider
    ] = lambda: storage
    yield application, storage
    application.dependency_overrides.clear()


@pytest.fixture
def practice_client(
    practice_application: tuple[FastAPI, PracticePhotoStorageStub],
    postgres_database: PostgresDatabase,
) -> Iterator[PracticeDraftClient]:
    application, storage = practice_application
    with TestClient(application, raise_server_exceptions=False) as client:
        yield PracticeDraftClient(client, storage, postgres_database)

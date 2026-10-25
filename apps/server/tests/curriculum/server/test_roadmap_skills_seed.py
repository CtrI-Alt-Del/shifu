from __future__ import annotations

from typing import TYPE_CHECKING

from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers.curriculum_content_provider import (
    DatabaseCurriculumContentProvider,
)
from shifu.shared.database.seed_data import (
    SEED_GRAPH_HTML_CSS_SKILL_ID,
    build_development_seed,
)

if TYPE_CHECKING:
    from tests.fixtures.postgres_fixture import PostgresDatabase

ROADMAP_ID_PREFIX = '01SHFRM'


def _store_curriculum(database: PostgresDatabase) -> SqlalchemyCurriculumDatabase:
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
    return curriculum_database


class TestRoadmapSkillsSeed:
    def test_should_make_every_roadmap_skill_startable(
        self, postgres_database: PostgresDatabase
    ) -> None:
        provider = DatabaseCurriculumContentProvider(
            _store_curriculum(postgres_database)
        )
        roadmap_skills = [
            skill
            for skill in provider.list_skill_content()
            if skill.id.startswith(ROADMAP_ID_PREFIX)
        ]

        assert len(roadmap_skills) >= 50
        not_ready = {
            skill.name: skill.v2_coverage_gaps
            for skill in roadmap_skills
            if not skill.v2_eligible
        }
        assert not_ready == {}

    def test_should_keep_graph_only_skills_without_content(
        self, postgres_database: PostgresDatabase
    ) -> None:
        provider = DatabaseCurriculumContentProvider(
            _store_curriculum(postgres_database)
        )

        skill = provider.get_skill_content(SEED_GRAPH_HTML_CSS_SKILL_ID)

        assert skill is not None
        assert skill.v2_eligible is False

    def test_should_link_roadmap_foundations_to_known_skills(self) -> None:
        seed = build_development_seed()
        skill_ids = {skill.id for skill in seed.skills}
        names = [skill.name for skill in seed.skills]

        assert len(names) == len(set(names))
        assert all(
            foundation.skill_id in skill_ids
            and foundation.foundation_skill_id in skill_ids
            for foundation in seed.skill_foundations
        )

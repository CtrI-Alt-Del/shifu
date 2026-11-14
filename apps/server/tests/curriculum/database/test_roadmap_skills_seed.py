from shifu.curriculum.database.roadmap_skills_seed import build_roadmap_skills_seed


class TestRoadmapSkillsSeed:
    def test_should_build_the_same_catalog_text_on_every_seed(self) -> None:
        # The Mentor index version hashes the catalog text; random placeholder
        # text would make every reseed leave the index stale.
        anchors = {
            'logic': '01SHF000000000000000000200',
            'javascript': '01SHF000000000000000000205',
            'apis': '01SHF000000000000000000204',
        }

        first = build_roadmap_skills_seed(anchors)
        second = build_roadmap_skills_seed(anchors)

        assert [
            (activity.id, activity.title, activity.objective)
            for activity in first.activities
        ] == [
            (activity.id, activity.title, activity.objective)
            for activity in second.activities
        ]
        assert [(material.id, material.title) for material in first.materials] == [
            (material.id, material.title) for material in second.materials
        ]

from typing import Protocol

from shifu.learning.core.domain.entities import SkillExperience


class SkillExperiencesRepository(Protocol):
    def find_by_id(
        self,
        skill_experience_id: str,
    ) -> SkillExperience | None: ...

    def find_by_goal_id_and_skill_id(
        self,
        goal_id: str,
        skill_id: str,
    ) -> SkillExperience | None: ...

    def find_many_by_goal_id(self, goal_id: str) -> list[SkillExperience]: ...

    def add(self, skill_experience: SkillExperience) -> None: ...

    def add_many(self, skill_experiences: list[SkillExperience]) -> None: ...

    def update(self, skill_experience: SkillExperience) -> None: ...

    def remove(self, skill_experience: SkillExperience) -> None: ...

    def remove_all(self) -> None: ...

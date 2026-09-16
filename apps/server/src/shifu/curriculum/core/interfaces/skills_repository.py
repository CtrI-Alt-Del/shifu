from typing import Protocol

from shifu.curriculum.core.domain.entities import Skill


class SkillsRepository(Protocol):
    def find_by_id(self, skill_id: str) -> Skill | None: ...

    def find_many_by_ids(self, skill_ids: tuple[str, ...]) -> list[Skill]: ...

    def find_all(self) -> list[Skill]: ...

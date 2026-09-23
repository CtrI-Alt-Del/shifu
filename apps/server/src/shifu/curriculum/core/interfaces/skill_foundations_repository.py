from typing import Protocol

from shifu.curriculum.core.domain.structures import SkillFoundation


class SkillFoundationsRepository(Protocol):
    def find_many_by_skill_id(self, skill_id: str) -> list[SkillFoundation]: ...

    def find_many_by_skill_ids(
        self, skill_ids: list[str]
    ) -> dict[str, list[SkillFoundation]]: ...

    def find_many_by_foundation_skill_id(
        self,
        foundation_skill_id: str,
    ) -> list[SkillFoundation]: ...

    def find_all(self) -> list[SkillFoundation]: ...

    def add_many(self, foundations: list[SkillFoundation]) -> None: ...

    def remove_all(self) -> None: ...

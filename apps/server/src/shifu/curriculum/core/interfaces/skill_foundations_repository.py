from typing import Protocol

from shifu.curriculum.core.domain.structures import SkillFoundation


class SkillFoundationsRepository(Protocol):
    def find_many_by_skill_id(self, skill_id: str) -> list[SkillFoundation]: ...

    def find_many_by_foundation_skill_id(
        self,
        foundation_skill_id: str,
    ) -> list[SkillFoundation]: ...

    def find_all(self) -> list[SkillFoundation]: ...

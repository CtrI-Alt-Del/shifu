from typing import Protocol

from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumSkillSnapshot,
)


class CurriculumContentProvider(Protocol):
    def get_skill_content(self, skill_id: str) -> CurriculumSkillSnapshot | None: ...

    def get_choice_activity(
        self,
        activity_id: str,
    ) -> CurriculumChoiceActivitySnapshot | None: ...

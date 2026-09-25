from typing import Protocol

from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumMaterialContentSnapshot,
    CurriculumSkillOverview,
    CurriculumSkillSnapshot,
)


class CurriculumContentProvider(Protocol):
    def list_skill_content(self) -> tuple[CurriculumSkillSnapshot, ...]: ...

    def get_skill_content(self, skill_id: str) -> CurriculumSkillSnapshot | None: ...

    def get_material_content(
        self, material_id: str
    ) -> CurriculumMaterialContentSnapshot | None: ...

    def get_choice_activity(
        self,
        activity_id: str,
    ) -> CurriculumChoiceActivitySnapshot | None: ...

    def get_skill_overviews(
        self,
        skill_ids: tuple[str, ...],
    ) -> tuple[CurriculumSkillOverview, ...]: ...

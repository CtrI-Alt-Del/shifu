from shifu.learning.core.domain.enums import CompetencyAvailability
from shifu.learning.core.domain.errors import MaterialDetailNotFoundError
from shifu.learning.core.domain.structures import (
    AvailableMaterialDetail,
    CompetencyMaterialDetail,
    MaterialDetail,
    UnavailableMaterialDetail,
)
from shifu.learning.core.use_cases.get_competency_detail_use_case import (
    GetCompetencyDetailUseCase,
)
from shifu.shared.core.interfaces import CurriculumContentProvider


class GetMaterialDetailUseCase:
    def __init__(
        self,
        get_competency_detail_use_case: GetCompetencyDetailUseCase,
        curriculum_content_provider: CurriculumContentProvider,
    ) -> None:
        self._get_competency_detail_use_case = get_competency_detail_use_case
        self._curriculum_content_provider = curriculum_content_provider

    def execute(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        competency_id: str,
        material_id: str,
    ) -> MaterialDetail:
        competency_detail = self._get_competency_detail_use_case.execute(
            account_id,
            goal_id,
            skill_id,
            competency_id,
        )

        if competency_detail.availability is CompetencyAvailability.UNAVAILABLE:
            return UnavailableMaterialDetail(
                goal_id=competency_detail.goal_id,
                skill_id=competency_detail.skill_id,
                skill_name=competency_detail.skill_name,
                competency_id=competency_detail.competency_id,
                competency_name=competency_detail.competency_name,
                material_id=material_id,
                availability=CompetencyAvailability.UNAVAILABLE,
                focus_competency_id=competency_detail.focus_competency_id,
                focus_competency_name=competency_detail.focus_competency_name,
            )

        material_item = next(
            (
                item
                for item in competency_detail.items
                if isinstance(item, CompetencyMaterialDetail) and item.id == material_id
            ),
            None,
        )
        if material_item is None:
            raise MaterialDetailNotFoundError

        content = self._curriculum_content_provider.get_material_content(material_id)
        if (
            content is None
            or content.id != material_id
            or content.skill_id != competency_detail.skill_id
        ):
            raise MaterialDetailNotFoundError

        return AvailableMaterialDetail(
            goal_id=competency_detail.goal_id,
            skill_id=competency_detail.skill_id,
            skill_name=competency_detail.skill_name,
            competency_id=competency_detail.competency_id,
            competency_name=competency_detail.competency_name,
            material_id=content.id,
            material_title=content.title,
            availability=CompetencyAvailability.AVAILABLE,
            content=content.content,
            recommendation=competency_detail.recommendation,
        )

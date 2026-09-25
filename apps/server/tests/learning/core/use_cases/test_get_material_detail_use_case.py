from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from shifu.learning.core.domain.enums import (
    ActivityDifficulty,
    ActivityRecommendationType,
    CompetencyAvailability,
    CompetencyProgressStatus,
)
from shifu.learning.core.domain.errors import (
    CompetencyDetailNotFoundError,
    MaterialDetailNotFoundError,
)
from shifu.learning.core.domain.structures import (
    ActivityRecommendation,
    AvailableCompetencyDetail,
    AvailableMaterialDetail,
    CompetencyActivityDetail,
    CompetencyMaterialDetail,
    UnavailableCompetencyDetail,
    UnavailableMaterialDetail,
)
from shifu.learning.core.use_cases import (
    GetCompetencyDetailUseCase,
    GetMaterialDetailUseCase,
)
from shifu.shared.core.domain.structures import CurriculumMaterialContentSnapshot
from shifu.shared.core.interfaces import CurriculumContentProvider

ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
SKILL_ID = 'skill-1'
COMPETENCY_ID = 'competency-1'
MATERIAL_ID = 'material-1'
OTHER_MATERIAL_ID = 'material-2'
ACTIVITY_ID = 'activity-1'
MARKDOWN = 'Um parágrafo.\n\n```python\nprint(1)\n```'


def recommendation() -> ActivityRecommendation:
    return ActivityRecommendation(
        competency_id=COMPETENCY_ID,
        activity_id=ACTIVITY_ID,
        difficulty=ActivityDifficulty.EASY,
        type=ActivityRecommendationType.NEW_ACTIVITY,
    )


def available_competency(
    *,
    items: tuple[CompetencyMaterialDetail | CompetencyActivityDetail, ...] = (),
    activity_recommendation: ActivityRecommendation | None = None,
) -> AvailableCompetencyDetail:
    return AvailableCompetencyDetail(
        goal_id=GOAL_ID,
        skill_id=SKILL_ID,
        skill_name='Lógica de programação',
        competency_id=COMPETENCY_ID,
        competency_name='Estruturas de repetição',
        availability=CompetencyAvailability.AVAILABLE,
        progress=Decimal('40'),
        status=CompetencyProgressStatus.DEVELOPING,
        is_focus=activity_recommendation is not None,
        focus_returned=False,
        focus_competency_id=COMPETENCY_ID,
        focus_competency_name='Estruturas de repetição',
        items=items,
        recommendation=activity_recommendation,
    )


def material_item(material_id: str = MATERIAL_ID) -> CompetencyMaterialDetail:
    return CompetencyMaterialDetail(id=material_id, title='Repetição', position=1)


def content(
    *,
    material_id: str = MATERIAL_ID,
    skill_id: str = SKILL_ID,
    body: str = MARKDOWN,
) -> CurriculumMaterialContentSnapshot:
    return CurriculumMaterialContentSnapshot(
        id=material_id,
        skill_id=skill_id,
        title='Repetição com for',
        material_type='reference',
        content=body,
    )


class TestGetMaterialDetailUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.competency_detail_use_case = create_autospec(
            GetCompetencyDetailUseCase,
            instance=True,
        )
        self.curriculum_content_provider = create_autospec(
            CurriculumContentProvider,
            instance=True,
        )
        self.use_case = GetMaterialDetailUseCase(
            self.competency_detail_use_case,
            self.curriculum_content_provider,
        )

    def execute(self, material_id: str = MATERIAL_ID) -> object:
        return self.use_case.execute(
            ACCOUNT_ID,
            GOAL_ID,
            SKILL_ID,
            COMPETENCY_ID,
            material_id,
        )

    def test_should_return_the_official_markdown_of_a_released_material(self) -> None:
        self.competency_detail_use_case.execute.return_value = available_competency(
            items=(material_item(),)
        )
        self.curriculum_content_provider.get_material_content.return_value = content()

        detail = self.execute()

        assert isinstance(detail, AvailableMaterialDetail)
        assert detail.availability is CompetencyAvailability.AVAILABLE
        assert detail.content == MARKDOWN
        assert detail.material_id == MATERIAL_ID
        assert detail.material_title == 'Repetição com for'
        assert detail.competency_id == COMPETENCY_ID
        assert detail.competency_name == 'Estruturas de repetição'
        assert detail.skill_name == 'Lógica de programação'
        self.competency_detail_use_case.execute.assert_called_once_with(
            ACCOUNT_ID,
            GOAL_ID,
            SKILL_ID,
            COMPETENCY_ID,
        )
        self.curriculum_content_provider.get_material_content.assert_called_once_with(
            MATERIAL_ID
        )

    def test_should_reuse_the_current_recommendation_of_the_source_competency(
        self,
    ) -> None:
        self.competency_detail_use_case.execute.return_value = available_competency(
            items=(material_item(),),
            activity_recommendation=recommendation(),
        )
        self.curriculum_content_provider.get_material_content.return_value = content()

        detail = self.execute()

        assert isinstance(detail, AvailableMaterialDetail)
        assert detail.recommendation == recommendation()
        assert detail.recommendation is not None
        assert detail.recommendation.competency_id == COMPETENCY_ID

    def test_should_omit_the_recommendation_when_the_competency_has_none(self) -> None:
        self.competency_detail_use_case.execute.return_value = available_competency(
            items=(material_item(),)
        )
        self.curriculum_content_provider.get_material_content.return_value = content()

        detail = self.execute()

        assert isinstance(detail, AvailableMaterialDetail)
        assert detail.recommendation is None

    def test_should_preserve_the_competency_of_origin_in_the_response(self) -> None:
        self.competency_detail_use_case.execute.return_value = available_competency(
            items=(material_item(),),
            activity_recommendation=recommendation(),
        )
        self.curriculum_content_provider.get_material_content.return_value = content()

        detail = self.execute()

        assert isinstance(detail, AvailableMaterialDetail)
        assert detail.goal_id == GOAL_ID
        assert detail.skill_id == SKILL_ID
        assert detail.competency_id == COMPETENCY_ID

    def test_should_restrict_the_material_when_the_competency_is_not_released(
        self,
    ) -> None:
        self.competency_detail_use_case.execute.return_value = (
            UnavailableCompetencyDetail(
                goal_id=GOAL_ID,
                skill_id=SKILL_ID,
                skill_name='Lógica de programação',
                competency_id=COMPETENCY_ID,
                competency_name='Estruturas de repetição',
                availability=CompetencyAvailability.UNAVAILABLE,
                focus_competency_id='competency-0',
                focus_competency_name='Variáveis',
            )
        )

        detail = self.execute()

        assert isinstance(detail, UnavailableMaterialDetail)
        assert detail.availability is CompetencyAvailability.UNAVAILABLE
        assert detail.focus_competency_name == 'Variáveis'
        assert detail.material_id == MATERIAL_ID
        self.curriculum_content_provider.get_material_content.assert_not_called()

    def test_should_reject_a_material_that_does_not_belong_to_the_competency(
        self,
    ) -> None:
        self.competency_detail_use_case.execute.return_value = available_competency(
            items=(material_item(OTHER_MATERIAL_ID),)
        )

        with pytest.raises(MaterialDetailNotFoundError):
            self.execute()

        self.curriculum_content_provider.get_material_content.assert_not_called()

    def test_should_reject_an_activity_identifier_used_as_a_material(self) -> None:
        self.competency_detail_use_case.execute.return_value = available_competency(
            items=(
                CompetencyActivityDetail(
                    id=MATERIAL_ID,
                    title='Atividade',
                    position=1,
                    activity_type='learning',
                    difficulty=ActivityDifficulty.EASY,
                    latest_score=None,
                ),
            )
        )

        with pytest.raises(MaterialDetailNotFoundError):
            self.execute()

        self.curriculum_content_provider.get_material_content.assert_not_called()

    def test_should_reject_a_material_missing_from_the_curriculum(self) -> None:
        self.competency_detail_use_case.execute.return_value = available_competency(
            items=(material_item(),)
        )
        self.curriculum_content_provider.get_material_content.return_value = None

        with pytest.raises(MaterialDetailNotFoundError):
            self.execute()

    def test_should_reject_curriculum_content_from_another_skill(self) -> None:
        self.competency_detail_use_case.execute.return_value = available_competency(
            items=(material_item(),)
        )
        self.curriculum_content_provider.get_material_content.return_value = content(
            skill_id='skill-2'
        )

        with pytest.raises(MaterialDetailNotFoundError):
            self.execute()

    def test_should_propagate_the_private_absence_of_the_competency(self) -> None:
        self.competency_detail_use_case.execute.side_effect = (
            CompetencyDetailNotFoundError
        )

        with pytest.raises(CompetencyDetailNotFoundError):
            self.execute()

        self.curriculum_content_provider.get_material_content.assert_not_called()

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.core.domain.enums import MilestoneKind, XpSource
from shifu.gamification.core.domain.structures import XpOrigin
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases import GrantXpUseCase
from shifu.gamification.core.use_cases.recognize_competency_mastered_use_case import (
    RecognizeCompetencyMasteredUseCase,
)
from shifu.shared.core.domain.structures import (
    CurriculumCompetencySnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider, IdentifierProvider

ACCOUNT_ID = 'account-1'
SKILL_ID = 'skill-1'
COMPETENCY_ID = 'skill-1-competency-2'
SKILL_EXPERIENCE_ID = 'skill-experience-1'
GRANT_ID = 'grant-1'
MILESTONE_ID = 'milestone-1'
NOW = datetime(2026, 1, 1, tzinfo=UTC)
OCCURRED_AT = datetime(2025, 6, 15, tzinfo=UTC)

_FALLBACK_LABEL = 'Competência dominada pela primeira vez'

_ORIGIN = XpOrigin(
    source=XpSource.COMPETENCY_MASTERY,
    reference_id=COMPETENCY_ID,
    label='Competency 2',
)


class TestRecognizeCompetencyMasteredUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(GamificationDatabase, instance=True)
        self.repositories = create_autospec(
            GamificationDatabaseRepositories,
            instance=True,
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.repositories.profiles.find_by_account_id.return_value = (
            GamificationProfileFaker.fake(account_id=ACCOUNT_ID)
        )
        self.repositories.rewarded_milestones.try_add.return_value = True
        self.curriculum_content_provider = create_autospec(
            CurriculumContentProvider,
            instance=True,
        )
        self.curriculum_content_provider.get_skill_content.return_value = (
            _skill_with_competencies(SKILL_ID, 3)
        )
        self.identifier_provider = create_autospec(IdentifierProvider, instance=True)
        self.identifier_provider.generate.side_effect = [GRANT_ID, MILESTONE_ID]
        self.grant_xp_use_case = create_autospec(GrantXpUseCase, instance=True)
        self.subject = RecognizeCompetencyMasteredUseCase(
            self.database,
            self.curriculum_content_provider,
            self.identifier_provider,
            self.grant_xp_use_case,
        )

    def test_should_grant_fifty_xp_on_first_mastery(self) -> None:
        self.subject.execute(
            ACCOUNT_ID,
            COMPETENCY_ID,
            SKILL_ID,
            SKILL_EXPERIENCE_ID,
            occurred_at=NOW,
            now=NOW,
        )

        milestone = self.repositories.rewarded_milestones.try_add.call_args.args[0]
        assert milestone.account_id == ACCOUNT_ID
        assert milestone.fact_id == SKILL_EXPERIENCE_ID
        assert milestone.kind is MilestoneKind.COMPETENCY_MASTERY
        assert milestone.subject_id == COMPETENCY_ID
        assert milestone.xp_grant_id == GRANT_ID
        assert milestone.rewarded_at == NOW
        self.grant_xp_use_case.apply_within_transaction.assert_called_once_with(
            self.repositories,
            ACCOUNT_ID,
            GRANT_ID,
            50,
            _ORIGIN,
            SKILL_EXPERIENCE_ID,
            occurred_at=NOW,
            now=NOW,
        )

    def test_should_label_the_origin_with_the_mastered_competency_name(self) -> None:
        self.subject.execute(
            ACCOUNT_ID,
            COMPETENCY_ID,
            SKILL_ID,
            SKILL_EXPERIENCE_ID,
            occurred_at=NOW,
            now=NOW,
        )

        origin = self.grant_xp_use_case.apply_within_transaction.call_args.args[4]
        assert origin.label == 'Competency 2'
        self.curriculum_content_provider.get_skill_content.assert_called_once_with(
            SKILL_ID
        )

    def test_should_fall_back_to_the_generic_label_when_the_skill_is_unknown(
        self,
    ) -> None:
        self.curriculum_content_provider.get_skill_content.return_value = None

        self.subject.execute(
            ACCOUNT_ID,
            COMPETENCY_ID,
            SKILL_ID,
            SKILL_EXPERIENCE_ID,
            occurred_at=NOW,
            now=NOW,
        )

        origin = self.grant_xp_use_case.apply_within_transaction.call_args.args[4]
        assert origin.label == _FALLBACK_LABEL

    def test_should_fall_back_when_the_competency_is_absent_from_the_skill(
        self,
    ) -> None:
        self.curriculum_content_provider.get_skill_content.return_value = (
            _skill_with_competencies('other-skill', 2)
        )

        self.subject.execute(
            ACCOUNT_ID,
            COMPETENCY_ID,
            SKILL_ID,
            SKILL_EXPERIENCE_ID,
            occurred_at=NOW,
            now=NOW,
        )

        origin = self.grant_xp_use_case.apply_within_transaction.call_args.args[4]
        assert origin.label == _FALLBACK_LABEL

    def test_should_pass_the_fact_date_as_occurred_at_not_the_processing_time(
        self,
    ) -> None:
        self.subject.execute(
            ACCOUNT_ID,
            COMPETENCY_ID,
            SKILL_ID,
            SKILL_EXPERIENCE_ID,
            occurred_at=OCCURRED_AT,
            now=NOW,
        )

        self.grant_xp_use_case.apply_within_transaction.assert_called_once_with(
            self.repositories,
            ACCOUNT_ID,
            GRANT_ID,
            50,
            _ORIGIN,
            SKILL_EXPERIENCE_ID,
            occurred_at=OCCURRED_AT,
            now=NOW,
        )

    def test_should_not_grant_xp_again_after_losing_and_regaining_mastery(
        self,
    ) -> None:
        self.repositories.rewarded_milestones.try_add.return_value = False

        self.subject.execute(
            ACCOUNT_ID,
            COMPETENCY_ID,
            SKILL_ID,
            SKILL_EXPERIENCE_ID,
            occurred_at=NOW,
            now=NOW,
        )

        self.grant_xp_use_case.apply_within_transaction.assert_not_called()
        # The subject lookup must stay behind the idempotency check: an
        # already-rewarded mastery does no Curriculum work at all.
        self.curriculum_content_provider.get_skill_content.assert_not_called()

    def test_should_no_op_when_profile_is_missing(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = None

        self.subject.execute(
            ACCOUNT_ID,
            COMPETENCY_ID,
            SKILL_ID,
            SKILL_EXPERIENCE_ID,
            occurred_at=NOW,
            now=NOW,
        )

        self.repositories.rewarded_milestones.try_add.assert_not_called()
        self.grant_xp_use_case.apply_within_transaction.assert_not_called()


def _skill_with_competencies(skill_id: str, count: int) -> CurriculumSkillSnapshot:
    return CurriculumSkillSnapshot(
        id=skill_id,
        name='Skill',
        competencies=tuple(
            CurriculumCompetencySnapshot(
                id=f'{skill_id}-competency-{position}',
                skill_id=skill_id,
                name=f'Competency {position}',
                position=position,
                items=(),
            )
            for position in range(1, count + 1)
        ),
    )

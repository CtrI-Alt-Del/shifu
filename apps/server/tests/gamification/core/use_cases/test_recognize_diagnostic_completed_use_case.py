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
from shifu.gamification.core.use_cases.recognize_diagnostic_completed_use_case import (
    RecognizeDiagnosticCompletedUseCase,
)
from shifu.shared.core.domain.structures import (
    CurriculumCompetencySnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider, IdentifierProvider

ACCOUNT_ID = 'account-1'
SKILL_ID = 'skill-1'
SKILL_EXPERIENCE_ID = 'skill-experience-1'
GRANT_ID = 'grant-1'
MILESTONE_ID = 'milestone-1'
NOW = datetime(2026, 1, 1, tzinfo=UTC)
OCCURRED_AT = datetime(2025, 6, 15, tzinfo=UTC)


class TestRecognizeDiagnosticCompletedUseCase:
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
        self.subject = RecognizeDiagnosticCompletedUseCase(
            self.database,
            self.curriculum_content_provider,
            self.identifier_provider,
            self.grant_xp_use_case,
        )

    def test_should_grant_xp_for_each_competency_on_first_completion(self) -> None:
        self.subject.execute(
            ACCOUNT_ID, SKILL_ID, SKILL_EXPERIENCE_ID, occurred_at=NOW, now=NOW
        )

        milestone = self.repositories.rewarded_milestones.try_add.call_args.args[0]
        assert milestone.account_id == ACCOUNT_ID
        assert milestone.fact_id == SKILL_EXPERIENCE_ID
        assert milestone.kind is MilestoneKind.DIAGNOSIS
        assert milestone.subject_id == SKILL_ID
        assert milestone.xp_grant_id == GRANT_ID
        assert milestone.rewarded_at == NOW
        self.grant_xp_use_case.apply_within_transaction.assert_called_once_with(
            self.repositories,
            ACCOUNT_ID,
            GRANT_ID,
            60,
            XpOrigin(
                source=XpSource.DIAGNOSIS,
                reference_id=SKILL_ID,
                label='Diagnóstico concluído: Skill',
            ),
            SKILL_EXPERIENCE_ID,
            occurred_at=NOW,
            now=NOW,
        )

    def test_should_pass_the_fact_date_as_occurred_at_not_the_processing_time(
        self,
    ) -> None:
        self.subject.execute(
            ACCOUNT_ID,
            SKILL_ID,
            SKILL_EXPERIENCE_ID,
            occurred_at=OCCURRED_AT,
            now=NOW,
        )

        self.grant_xp_use_case.apply_within_transaction.assert_called_once_with(
            self.repositories,
            ACCOUNT_ID,
            GRANT_ID,
            60,
            XpOrigin(
                source=XpSource.DIAGNOSIS,
                reference_id=SKILL_ID,
                label='Diagnóstico concluído: Skill',
            ),
            SKILL_EXPERIENCE_ID,
            occurred_at=OCCURRED_AT,
            now=NOW,
        )

    def test_should_not_grant_xp_again_for_the_same_skill_under_another_objetivo(
        self,
    ) -> None:
        self.repositories.rewarded_milestones.try_add.return_value = False

        self.subject.execute(
            ACCOUNT_ID, SKILL_ID, SKILL_EXPERIENCE_ID, occurred_at=NOW, now=NOW
        )

        self.grant_xp_use_case.apply_within_transaction.assert_not_called()

    def test_should_no_op_when_profile_is_missing(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = None

        self.subject.execute(
            ACCOUNT_ID, SKILL_ID, SKILL_EXPERIENCE_ID, occurred_at=NOW, now=NOW
        )

        self.repositories.rewarded_milestones.try_add.assert_not_called()
        self.grant_xp_use_case.apply_within_transaction.assert_not_called()

    def test_should_no_op_when_skill_is_unknown_to_curriculum(self) -> None:
        self.curriculum_content_provider.get_skill_content.return_value = None

        self.subject.execute(
            ACCOUNT_ID, SKILL_ID, SKILL_EXPERIENCE_ID, occurred_at=NOW, now=NOW
        )

        self.repositories.rewarded_milestones.try_add.assert_not_called()
        self.grant_xp_use_case.apply_within_transaction.assert_not_called()


def _skill_with_competencies(
    skill_id: str,
    count: int,
) -> CurriculumSkillSnapshot:
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

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from shifu.fakers.gamification.entities import (
    ActivityXpBalanceFaker,
    GamificationProfileFaker,
)
from shifu.gamification.core.domain.enums import XpSource
from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.gamification.core.domain.structures import XpOrigin
from shifu.gamification.core.interfaces import (
    GamificationDatabase,
    GamificationDatabaseRepositories,
)
from shifu.gamification.core.use_cases import GrantXpUseCase
from shifu.gamification.core.use_cases.recognize_activity_evaluated_use_case import (
    RecognizeActivityEvaluatedUseCase,
)
from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumChoicePartSnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider, IdentifierProvider

ACCOUNT_ID = 'account-1'
ACTIVITY_ID = 'activity-1'
ATTEMPT_ID = 'attempt-1'
GOAL_ID = 'goal-1'
SKILL_EXPERIENCE_ID = 'skill-experience-1'
GRANT_ID = 'grant-1'
RECOGNITION_ID = 'recognition-1'
BALANCE_ID = 'balance-1'
NOW = datetime(2026, 1, 1, tzinfo=UTC)
OCCURRED_AT = datetime(2025, 6, 15, tzinfo=UTC)

_FALLBACK_LABEL = 'Atividade avaliada'


def _activity(title: str = 'Atividade de teste') -> CurriculumChoiceActivitySnapshot:
    return CurriculumChoiceActivitySnapshot(
        id=ACTIVITY_ID,
        competency_id='competency-1',
        difficulty='easy',
        title=title,
        questions=(),
        parts=(
            CurriculumChoicePartSnapshot(
                question_key='question-1', weight_percentage=Decimal('100')
            ),
        ),
    )


class TestRecognizeActivityEvaluatedUseCase:
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
        self.repositories.activity_xp_balances.find_by_account_id_and_activity_id.return_value = None
        self.repositories.activity_xp_recognitions.try_add.return_value = True
        self.curriculum_content_provider = create_autospec(
            CurriculumContentProvider, instance=True
        )
        self.curriculum_content_provider.get_choice_activity.return_value = _activity()
        self.identifier_provider = create_autospec(IdentifierProvider, instance=True)
        # Default fixture has no existing balance, so generate() is called for
        # the new balance id first, then the grant id, then the recognition id.
        self.identifier_provider.generate.side_effect = [
            BALANCE_ID,
            GRANT_ID,
            RECOGNITION_ID,
        ]
        self.grant_xp_use_case = create_autospec(GrantXpUseCase, instance=True)
        self.subject = RecognizeActivityEvaluatedUseCase(
            self.database,
            self.curriculum_content_provider,
            self.identifier_provider,
            self.grant_xp_use_case,
        )

    def _execute(
        self,
        *,
        difficulty: str = 'easy',
        score: Decimal = Decimal('67'),
        occurred_at: datetime = NOW,
        now: datetime = NOW,
    ) -> None:
        self.subject.execute(
            ACCOUNT_ID,
            ACTIVITY_ID,
            ATTEMPT_ID,
            GOAL_ID,
            SKILL_EXPERIENCE_ID,
            difficulty=difficulty,
            score=score,
            occurred_at=occurred_at,
            now=now,
        )

    @pytest.mark.parametrize(
        ('difficulty', 'maximum', 'score', 'expected'),
        [
            ('easy', 10, Decimal('67'), 6),
            ('medium', 20, Decimal('67'), 13),
            ('hard', 30, Decimal('67'), 20),
            ('easy', 10, Decimal('100'), 10),
            ('easy', 10, Decimal('0'), 0),
            ('easy', 10, Decimal('1'), 0),
            ('easy', 10, Decimal('99.99'), 9),
        ],
    )
    def test_should_grant_the_floor_of_maximum_times_score_over_100(
        self, difficulty: str, maximum: int, score: Decimal, expected: int
    ) -> None:
        self._execute(difficulty=difficulty, score=score)

        if expected == 0:
            self.grant_xp_use_case.apply_within_transaction.assert_not_called()
            return
        self.grant_xp_use_case.apply_within_transaction.assert_called_once_with(
            self.repositories,
            ACCOUNT_ID,
            GRANT_ID,
            expected,
            XpOrigin(
                source=XpSource.ACTIVITY,
                reference_id=ACTIVITY_ID,
                label='Atividade de teste',
                goal_id=GOAL_ID,
                skill_experience_id=SKILL_EXPERIENCE_ID,
            ),
            ATTEMPT_ID,
            occurred_at=NOW,
            now=NOW,
        )

    def test_should_grant_only_the_remainder_when_a_balance_already_exists(
        self,
    ) -> None:
        self.repositories.activity_xp_balances.find_by_account_id_and_activity_id.return_value = ActivityXpBalanceFaker.fake(
            account_id=ACCOUNT_ID,
            activity_id=ACTIVITY_ID,
            maximum_xp=20,
            granted_xp=10,
            updated_at=OCCURRED_AT,
        )
        self.identifier_provider.generate.side_effect = [GRANT_ID, RECOGNITION_ID]

        self._execute(difficulty='medium', score=Decimal('80'))

        self.grant_xp_use_case.apply_within_transaction.assert_called_once_with(
            self.repositories,
            ACCOUNT_ID,
            GRANT_ID,
            6,
            XpOrigin(
                source=XpSource.ACTIVITY,
                reference_id=ACTIVITY_ID,
                label='Atividade de teste',
                goal_id=GOAL_ID,
                skill_experience_id=SKILL_EXPERIENCE_ID,
            ),
            ATTEMPT_ID,
            occurred_at=NOW,
            now=NOW,
        )
        self.repositories.activity_xp_balances.update.assert_called_once()
        self.repositories.activity_xp_balances.add.assert_not_called()

    def test_should_grant_nothing_when_the_activity_is_already_at_its_maximum(
        self,
    ) -> None:
        self.repositories.activity_xp_balances.find_by_account_id_and_activity_id.return_value = ActivityXpBalanceFaker.fake(
            account_id=ACCOUNT_ID,
            activity_id=ACTIVITY_ID,
            maximum_xp=10,
            granted_xp=10,
        )

        self._execute(difficulty='easy', score=Decimal('100'))

        self.grant_xp_use_case.apply_within_transaction.assert_not_called()
        self.repositories.activity_xp_recognitions.try_add.assert_called_once()
        recognition = self.repositories.activity_xp_recognitions.try_add.call_args.args[
            0
        ]
        assert recognition.granted_xp == 0
        assert recognition.xp_grant_id is None

    def test_should_write_no_recognition_second_time_when_already_processed(
        self,
    ) -> None:
        self.repositories.activity_xp_recognitions.try_add.return_value = False

        self._execute()

        self.grant_xp_use_case.apply_within_transaction.assert_not_called()
        self.repositories.activity_xp_balances.add.assert_not_called()
        self.repositories.activity_xp_balances.update.assert_not_called()

    def test_should_persist_a_new_balance_even_when_the_outcome_is_zero(self) -> None:
        self._execute(difficulty='easy', score=Decimal('0'))

        self.repositories.activity_xp_balances.add.assert_called_once()
        added = self.repositories.activity_xp_balances.add.call_args.args[0]
        assert added.granted_xp == 0
        assert added.maximum_xp == 10
        self.grant_xp_use_case.apply_within_transaction.assert_not_called()

    def test_should_use_the_attempt_id_as_the_fact_id(self) -> None:
        self._execute()

        fact_id = self.grant_xp_use_case.apply_within_transaction.call_args.args[5]
        assert fact_id == ATTEMPT_ID

    def test_should_fall_back_to_the_generic_label_when_the_activity_is_unknown(
        self,
    ) -> None:
        self.curriculum_content_provider.get_choice_activity.return_value = None

        self._execute()

        origin = self.grant_xp_use_case.apply_within_transaction.call_args.args[4]
        assert origin.label == _FALLBACK_LABEL

    def test_should_resolve_the_activity_title_after_the_idempotency_gate(
        self,
    ) -> None:
        self.repositories.activity_xp_recognitions.try_add.return_value = False

        self._execute()

        self.curriculum_content_provider.get_choice_activity.assert_not_called()

    def test_should_pass_the_fact_date_as_occurred_at_not_the_processing_time(
        self,
    ) -> None:
        self._execute(occurred_at=OCCURRED_AT, now=NOW)

        self.grant_xp_use_case.apply_within_transaction.assert_called_once_with(
            self.repositories,
            ACCOUNT_ID,
            GRANT_ID,
            6,
            XpOrigin(
                source=XpSource.ACTIVITY,
                reference_id=ACTIVITY_ID,
                label='Atividade de teste',
                goal_id=GOAL_ID,
                skill_experience_id=SKILL_EXPERIENCE_ID,
            ),
            ATTEMPT_ID,
            occurred_at=OCCURRED_AT,
            now=NOW,
        )

    def test_should_no_op_when_profile_is_missing(self) -> None:
        self.repositories.profiles.find_by_account_id.return_value = None

        self._execute()

        self.repositories.activity_xp_recognitions.try_add.assert_not_called()
        self.grant_xp_use_case.apply_within_transaction.assert_not_called()

    def test_should_raise_for_an_unmapped_difficulty(self) -> None:
        with pytest.raises(InvalidGamificationError):
            self._execute(difficulty='impossible')

        self.repositories.profiles.find_by_account_id.assert_not_called()

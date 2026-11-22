"""The private read of a practical preparation Activity: eligibility and public projection."""

from dataclasses import asdict
from decimal import Decimal

import pytest

from shifu.learning.core.domain.structures import (
    ChoiceActivityDetail,
    PracticalPreparationQuestionDetail,
)
from shifu.learning.core.use_cases import GetChoiceActivityUseCase
from shifu.shared.core.domain.errors import NotFoundError
from tests.learning.core.use_cases.practice_draft_use_case_setup import (
    ACCOUNT_ID,
    ACTIVITY_ID,
    COMPETENCY_ID,
    GOAL_ID,
    SKILL_ID,
    PracticeDraftUseCaseSetup,
    practical_snapshot,
)


class TestGetPracticalPreparationActivityUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.arrangement = PracticeDraftUseCaseSetup()
        repositories = self.arrangement.repositories
        repositories.ordering_passages.find_active.return_value = None
        repositories.activity_attempts.find_many_by_skill_experience_id_and_activity_id.return_value = []
        self.subject = GetChoiceActivityUseCase(
            self.arrangement.database, self.arrangement.curriculum
        )

    def _read(self) -> ChoiceActivityDetail:
        return self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
        )

    def test_should_return_the_rubric_with_public_weights(self) -> None:
        detail = self._read()

        (question,) = detail.questions
        assert isinstance(question, PracticalPreparationQuestionDetail)
        assert question.kind == 'practical_preparation'
        assert [record.key for record in question.records] == [
            'cuts',
            'during',
            'final',
        ]
        assert [(item.key, item.weight) for item in question.criteria] == [
            ('cut-regularity', Decimal(40)),
            ('observable-technique', Decimal(40)),
            ('presentation', Decimal(20)),
        ]
        assert question.guidance
        assert question.references[0].accessible_text
        assert detail.can_submit is True
        assert detail.activity_revision == 'revision-1'

    def test_should_not_expose_insufficiency_rules_levels_or_comments(self) -> None:
        detail = self._read()

        (question,) = detail.questions
        serialized = str(asdict(question))
        assert 'insufficiency' not in serialized
        assert 'inconclusive' not in serialized
        assert 'comment' not in serialized
        assert 'Refaça a foto dos cortes' not in serialized
        assert 'nível 100 observável' not in serialized

    def test_should_be_eligible_with_one_question(self) -> None:
        assert GetChoiceActivityUseCase.is_eligible(practical_snapshot()) is True

    def test_should_deny_another_account_without_revealing_the_activity(self) -> None:
        with pytest.raises(NotFoundError):
            self.subject.execute(
                'someone-else', GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
            )

    def test_should_deny_an_activity_of_another_competency(self) -> None:
        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID, GOAL_ID, SKILL_ID, 'competency-9', ACTIVITY_ID
            )

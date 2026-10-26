from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.enums import PlanningIntentKind
from shifu.intelligence.core.domain.errors import (
    PlanningClassificationUnavailableError,
)
from shifu.intelligence.core.domain.structures import (
    PlanningIntentClassification,
    PlanningQuery,
)
from shifu.intelligence.core.interfaces import PlanningIntentClassifierProvider
from shifu.intelligence.core.use_cases import ClassifyPlanningIntentUseCase
from shifu.shared.core.domain.errors import ServiceUnavailableError


def _classification(
    kind: PlanningIntentKind, confidence: float
) -> PlanningIntentClassification:
    rest = (1 - confidence) / 2
    return PlanningIntentClassification(
        kind=kind,
        confidence=confidence,
        probabilities=tuple(
            (candidate.value, confidence if candidate is kind else rest)
            for candidate in PlanningIntentKind
        ),
    )


class TestClassifyPlanningIntentUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.classifier = create_autospec(
            PlanningIntentClassifierProvider, instance=True
        )
        self.use_case = ClassifyPlanningIntentUseCase(self.classifier)
        self.query = PlanningQuery(
            intent='Quero aprender a programar do zero',
            answers=('Nunca programei', 'Quero trabalhar com web'),
        )

    def test_should_expose_exactly_the_three_planning_kinds(self) -> None:
        self.classifier.classify.side_effect = [
            _classification(kind, 0.9) for kind in PlanningIntentKind
        ]
        assert [
            self.use_case.execute(self.query).kind.value for _kind in PlanningIntentKind
        ] == ['learning', 'out-of-scope', 'ambiguous']
        assert self.classifier.classify.call_count == 3

    def test_should_return_the_learning_decision_for_the_submitted_query(self) -> None:
        expected = _classification(PlanningIntentKind.LEARNING, 0.92)
        self.classifier.classify.return_value = expected

        result = self.use_case.execute(self.query)

        assert result == expected
        self.classifier.classify.assert_called_once_with(self.query)

    def test_should_report_a_refusal_as_a_decision_rather_than_an_error(self) -> None:
        expected = _classification(PlanningIntentKind.OUT_OF_SCOPE, 0.88)
        self.classifier.classify.return_value = expected

        result = self.use_case.execute(self.query)

        assert result.kind is PlanningIntentKind.OUT_OF_SCOPE
        assert result.confidence == 0.88

    def test_should_propagate_the_typed_classification_error(self) -> None:
        error = PlanningClassificationUnavailableError()
        self.classifier.classify.side_effect = error

        with pytest.raises(PlanningClassificationUnavailableError) as raised:
            self.use_case.execute(self.query)

        assert raised.value is error

    @pytest.mark.parametrize(
        'error', [ServiceUnavailableError(), ValueError('Malformed decision')]
    )
    def test_should_map_a_technical_failure_to_the_typed_error_instead_of_a_refusal(
        self, error: Exception
    ) -> None:
        self.classifier.classify.side_effect = error

        with pytest.raises(PlanningClassificationUnavailableError) as raised:
            self.use_case.execute(self.query)

        assert raised.value.__cause__ is error
        assert raised.value.message == (
            'A classificação da intenção do Planejador está indisponível.'
        )

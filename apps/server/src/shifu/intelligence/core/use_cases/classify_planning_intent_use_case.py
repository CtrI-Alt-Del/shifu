from shifu.intelligence.core.domain.errors import (
    PlanningClassificationUnavailableError,
)
from shifu.intelligence.core.domain.structures import (
    PlanningIntentClassification,
    PlanningQuery,
)
from shifu.intelligence.core.interfaces import PlanningIntentClassifierProvider
from shifu.shared.core.domain.errors import ServiceUnavailableError


class ClassifyPlanningIntentUseCase:
    def __init__(self, classifier: PlanningIntentClassifierProvider) -> None:
        self._classifier = classifier

    def execute(self, query: PlanningQuery) -> PlanningIntentClassification:
        try:
            return self._classifier.classify(query)
        except PlanningClassificationUnavailableError:
            raise
        except (ServiceUnavailableError, ValueError) as error:
            # A technical failure is never reported as a refusal by scope.
            raise PlanningClassificationUnavailableError from error

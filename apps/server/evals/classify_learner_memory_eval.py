from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from time import monotonic
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from evals.common import CaseDefinition, select_definitions
from shifu.intelligence.ai.data.learner_memory_resources import LearnerMemoryResources

if TYPE_CHECKING:
    from collections.abc import Callable

    from shifu.intelligence.core.domain.structures import LearnerMemoryAnalysis


class _Analyzer(Protocol):
    def analyze(self, text: str) -> LearnerMemoryAnalysis: ...


_NO_MEMORY = 'nenhuma'
_CASE_FOR_LABEL = {
    'explanation_preference': 'explanation_preference_precision_recall',
    'declared_knowledge': 'declared_knowledge_precision_recall',
    'interest_or_intention': 'interest_or_intention_precision_recall',
    'recurring_difficulty': 'recurring_difficulty_precision_recall',
    _NO_MEMORY: 'no_memory_false_positive_rate',
}


@cache
def _resources() -> LearnerMemoryResources:
    return LearnerMemoryResources()


@dataclass(frozen=True)
class _Prediction:
    text: str
    expected: str
    actual: str


class ClassifyLearnerMemoryEval:
    """Gate the local TF-IDF 3-NN classifier on the versioned synthetic pt-BR set (RF-19)."""

    selector = 'classify-learner-memory'
    workflow_id = 'intelligence-classify-learner-memory'
    prompt_revision = 'tfidf-3nn-count-bow-v1'
    PRECISION: ClassVar[float] = 0.90
    RECALL: ClassVar[float] = 0.70
    FALSE_POSITIVE_RATE: ClassVar[float] = 0.05

    def __init__(
        self,
        analyzer: _Analyzer,
        *,
        mode: str,
        model_profile: str,
        close_resources: Callable[[], None] | None = None,
    ) -> None:
        self._analyzer = analyzer
        self._mode = mode
        self._model_profile = model_profile
        self._close_resources = close_resources

    @property
    def dataset_revision(self) -> str:
        return _resources().dataset_revision

    @classmethod
    def definitions(cls) -> tuple[CaseDefinition, ...]:
        cases = _resources().evaluation
        return tuple(
            CaseDefinition(
                name=name,
                tags=(
                    ('false-positive', 'no-memory')
                    if label == _NO_MEMORY
                    else ('precision-recall', label)
                ),
                input=f'{sum(1 for case in cases if case.label == label)} synthetic pt-BR sentences',
                expected=(
                    {'max_false_positive_rate': cls.FALSE_POSITIVE_RATE}
                    if label == _NO_MEMORY
                    else {
                        'min_precision': cls.PRECISION,
                        'min_recall': cls.RECALL,
                    }
                ),
            )
            for label, name in _CASE_FOR_LABEL.items()
        )

    def run(self, name: str | None = None, tag: str | None = None) -> dict[str, Any]:
        definitions = self.definitions()
        selected = select_definitions(definitions, name=name, tag=tag)
        started = monotonic()
        try:
            predictions: tuple[_Prediction, ...] | None = self._predict()
        except Exception:  # noqa: BLE001 - analyzer errors can contain sentence text.
            predictions = None
        duration = round(max(monotonic() - started, 0.0), 3)

        case_reports: list[dict[str, Any]] = []
        for definition in selected:
            label = next(
                label
                for label, case in _CASE_FOR_LABEL.items()
                if case == definition.name
            )
            if predictions is None:
                case_reports.append(self._failed(definition.name, duration))
            else:
                case_reports.append(
                    self._score(definition.name, label, predictions, duration)
                )
        successful = bool(case_reports) and all(
            item['outcome'] == 'passed' for item in case_reports
        )
        report: dict[str, Any] = {
            'workflow': self.selector,
            'status': 'passed' if successful else 'failed',
            'partial': len(selected) < len(definitions),
            'mode': self._mode,
            'model_profile': self._model_profile,
            'dataset_revision': self.dataset_revision,
            'prompt_revision': self.prompt_revision,
            'selected_case_ids': [definition.name for definition in selected],
            'counts': {
                'selected': len(case_reports),
                'passed': sum(item['outcome'] == 'passed' for item in case_reports),
                'failed': sum(item['outcome'] == 'failed' for item in case_reports),
                'skipped': 0,
            },
            'cases': case_reports,
        }
        if predictions is not None:
            report['per_class'] = {
                label: self._class_metrics(label, predictions)
                for label in _CASE_FOR_LABEL
            }
            report['misclassified'] = [
                {
                    'text': item.text,
                    'expected': item.expected,
                    'actual': item.actual,
                }
                for item in predictions
                if item.expected != item.actual
            ]
        return report

    def close(self) -> None:
        if self._close_resources is not None:
            self._close_resources()

    def _predict(self) -> tuple[_Prediction, ...]:
        predictions: list[_Prediction] = []
        for case in _resources().evaluation:
            analysis = self._analyzer.analyze(case.text)
            actual = (
                analysis.statements[0].category.value
                if analysis.statements
                else _NO_MEMORY
            )
            predictions.append(_Prediction(case.text, case.label, actual))
        return tuple(predictions)

    @staticmethod
    def _class_metrics(
        label: str, predictions: tuple[_Prediction, ...]
    ) -> dict[str, Any]:
        true_positive = sum(
            1 for item in predictions if item.expected == label == item.actual
        )
        false_positive = sum(
            1 for item in predictions if item.actual == label != item.expected
        )
        false_negative = sum(
            1 for item in predictions if item.expected == label != item.actual
        )
        support = true_positive + false_negative
        predicted = true_positive + false_positive
        metrics: dict[str, Any] = {
            'support': support,
            'true_positive': true_positive,
            'false_positive': false_positive,
            'false_negative': false_negative,
            'precision': round(true_positive / predicted, 3) if predicted else 0.0,
            'recall': round(true_positive / support, 3) if support else 0.0,
        }
        if label == _NO_MEMORY:
            memories = sum(
                1
                for item in predictions
                if item.expected == _NO_MEMORY and item.actual != _NO_MEMORY
            )
            metrics['false_positive_rate'] = (
                round(memories / support, 3) if support else 1.0
            )
        return metrics

    def _score(
        self,
        name: str,
        label: str,
        predictions: tuple[_Prediction, ...],
        duration: float,
    ) -> dict[str, Any]:
        metrics = self._class_metrics(label, predictions)
        if label == _NO_MEMORY:
            passed = (
                metrics['support'] > 0
                and metrics['false_positive_rate'] <= self.FALSE_POSITIVE_RATE
            )
        else:
            passed = (
                metrics['precision'] >= self.PRECISION
                and metrics['recall'] >= self.RECALL
            )
        metrics['misclassified'] = [
            {'text': item.text, 'expected': item.expected, 'actual': item.actual}
            for item in predictions
            if item.expected != item.actual and label in {item.expected, item.actual}
        ]
        return {
            'case_id': name,
            'outcome': 'passed' if passed else 'failed',
            'duration_seconds': duration,
            'skipped': False,
            'scorer_passed': passed,
            'failure_code': None if passed else 'classification_gate_not_met',
            'metrics': metrics,
        }

    @staticmethod
    def _failed(name: str, duration: float) -> dict[str, Any]:
        return {
            'case_id': name,
            'outcome': 'failed',
            'duration_seconds': duration,
            'skipped': False,
            'scorer_passed': False,
            'failure_code': 'analyzer_unavailable',
            'metrics': {},
        }

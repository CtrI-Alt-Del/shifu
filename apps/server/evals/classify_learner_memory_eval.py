from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from time import monotonic
from typing import Any, ClassVar

from shifu.intelligence.ai.data.learner_memory_resources import LearnerMemoryResources
from shifu.intelligence.providers.memory_classification.tfidf.tfidf_learner_memory_analyzer_provider import (
    TfidfLearnerMemoryAnalyzerProvider,
)
from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
    SpacyMentorTextPreprocessorProvider,
)

from evals.eval import Eval


class ClassifyLearnerMemoryEval(Eval):
    """Gate the local TF-IDF 3-NN classifier on the versioned synthetic pt-BR set.

    Local NLP only: identical in double and real modes, no model calls.
    """

    selector = 'classify-learner-memory'
    workflow_id = 'intelligence-classify-learner-memory'
    prompt_revision = 'tfidf-3nn-count-bow-v1'
    unavailable_failure_code = 'analyzer_unavailable'
    PRECISION: ClassVar[float] = 0.90
    RECALL: ClassVar[float] = 0.70
    FALSE_POSITIVE_RATE: ClassVar[float] = 0.05
    NO_MEMORY: ClassVar[str] = 'nenhuma'
    CASE_FOR_LABEL: ClassVar[dict[str, str]] = {
        'explanation_preference': 'explanation_preference_precision_recall',
        'declared_knowledge': 'declared_knowledge_precision_recall',
        'interest_or_intention': 'interest_or_intention_precision_recall',
        'recurring_difficulty': 'recurring_difficulty_precision_recall',
        'nenhuma': 'no_memory_false_positive_rate',
    }

    @dataclass(frozen=True)
    class Prediction:
        text: str
        expected: str
        actual: str

    def __init__(self, *, mode: str) -> None:
        super().__init__(mode=mode)
        self.analyzer = TfidfLearnerMemoryAnalyzerProvider(
            SpacyMentorTextPreprocessorProvider(), self.resources()
        )
        self.model_profile = 'local-tfidf-3nn'
        self.predictions: tuple[ClassifyLearnerMemoryEval.Prediction, ...] | None = None

    @property
    def dataset_revision(self) -> str:
        return self.resources().dataset_revision

    @staticmethod
    @cache
    def resources() -> LearnerMemoryResources:
        return LearnerMemoryResources()

    def cases(self) -> tuple[Eval.LocalCase, ...]:
        sentences = self.resources().evaluation
        return tuple(
            Eval.LocalCase(
                name=name,
                tags=(
                    ('false-positive', 'no-memory')
                    if label == self.NO_MEMORY
                    else ('precision-recall', label)
                ),
                input=f'{sum(1 for case in sentences if case.label == label)} synthetic pt-BR sentences',
                expected=(
                    {'max_false_positive_rate': self.FALSE_POSITIVE_RATE}
                    if label == self.NO_MEMORY
                    else {'min_precision': self.PRECISION, 'min_recall': self.RECALL}
                ),
            )
            for label, name in self.CASE_FOR_LABEL.items()
        )

    def run_local_cases(self, selected: tuple[Any, ...]) -> list[dict[str, Any]]:
        # One pass over the whole set serves every per-label case.
        started = monotonic()
        try:
            self.predictions = self.predict()
        except Exception:  # noqa: BLE001 - analyzer errors can contain sentence text.
            self.predictions = None
        duration = monotonic() - started
        reports: list[dict[str, Any]] = []
        for case in selected:
            label = next(
                label
                for label, name in self.CASE_FOR_LABEL.items()
                if name == case.name
            )
            outcome = (
                self.CaseOutcome(
                    passed=False, failure_code=self.unavailable_failure_code, metrics={}
                )
                if self.predictions is None
                else self.score(label, self.predictions)
            )
            reports.append(
                self.local_case_report(case.name, outcome, duration=duration)
            )
        return reports

    def report_extras(self) -> dict[str, Any]:
        if self.predictions is None:
            return {}
        return {
            'per_class': {
                label: self.class_metrics(label, self.predictions)
                for label in self.CASE_FOR_LABEL
            },
            'misclassified': [
                {'text': item.text, 'expected': item.expected, 'actual': item.actual}
                for item in self.predictions
                if item.expected != item.actual
            ],
        }

    def predict(self) -> tuple[Prediction, ...]:
        predictions: list[ClassifyLearnerMemoryEval.Prediction] = []
        for case in self.resources().evaluation:
            analysis = self.analyzer.analyze(case.text)
            actual = (
                analysis.statements[0].category.value
                if analysis.statements
                else self.NO_MEMORY
            )
            predictions.append(self.Prediction(case.text, case.label, actual))
        return tuple(predictions)

    @classmethod
    def class_metrics(
        cls, label: str, predictions: tuple[Prediction, ...]
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
        if label == cls.NO_MEMORY:
            memories = sum(
                1
                for item in predictions
                if item.expected == cls.NO_MEMORY and item.actual != cls.NO_MEMORY
            )
            metrics['false_positive_rate'] = (
                round(memories / support, 3) if support else 1.0
            )
        return metrics

    def score(
        self, label: str, predictions: tuple[Prediction, ...]
    ) -> Eval.CaseOutcome:
        metrics = self.class_metrics(label, predictions)
        if label == self.NO_MEMORY:
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
        return self.CaseOutcome(
            passed, None if passed else 'classification_gate_not_met', metrics
        )

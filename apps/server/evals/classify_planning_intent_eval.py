from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import json
from time import monotonic
from typing import Any, ClassVar

import httpx

from shifu.intelligence.ai.data.planner_resources import PlannerResources
from shifu.intelligence.core.domain.enums import PlanningIntentKind
from shifu.intelligence.core.domain.structures import PlanningQuery
from shifu.intelligence.core.use_cases import ClassifyPlanningIntentUseCase
from shifu.intelligence.providers.planning.intent_classification.openrouter.jev_planning_intent_classifier_provider import (
    JevPlanningIntentClassifierProvider,
)
from shifu.shared.settings import get_settings

from evals.eval import Eval


class ClassifyPlanningIntentEval(Eval):
    """Gate the Jev Planner intent classifier on the versioned labeled pt-BR intents.

    Classifies every calibration and held-out intent of
    `planner-intent-evaluation.json` through the real `ClassifyPlanningIntentUseCase`
    and `JevPlanningIntentClassifierProvider`, with the manifest thresholds. Real mode
    calls the OpenRouter decisions endpoint; double mode answers each request with its
    own label through an HTTP transport double, so only the plumbing is exercised.
    The held-out set gates accuracy; no learning intent may ever be refused.
    """

    selector = 'classify-planning-intent'
    workflow_id = 'intelligence-classify-planning-intent'
    prompt_revision = 'jev-planning-intent-criteria-v2'
    unavailable_failure_code = 'classifier_unavailable'
    HELD_OUT_ACCURACY: ClassVar[float] = 0.90
    SECTIONS: ClassVar[tuple[str, ...]] = ('calibration', 'held_out')
    ACCURACY_CASE: ClassVar[str] = 'held_out_accuracy'
    REFUSAL_CASE: ClassVar[str] = 'learning_never_refused'
    DOUBLE_CONFIDENCE: ClassVar[float] = 0.9
    WORKERS: ClassVar[int] = 8

    @dataclass(frozen=True)
    class Sample:
        section: str
        text: str
        expected: PlanningIntentKind
        actual: PlanningIntentKind | None = None
        confidence: float | None = None

    def __init__(self, *, mode: str) -> None:
        super().__init__(mode=mode)
        self.resources = PlannerResources()
        self.model_profile = (
            'synthetic-jev-double'
            if self.double
            else self.resources.manifest.classifier_model
        )
        self.samples: tuple[ClassifyPlanningIntentEval.Sample, ...] | None = None

    @property
    def dataset_revision(self) -> str:
        evaluation = self.resources.intent_evaluation.model_dump()
        digest = hashlib.sha256(
            json.dumps(
                evaluation, sort_keys=True, ensure_ascii=False, separators=(',', ':')
            ).encode()
        ).hexdigest()
        return f'planner-intents-synthetic-{digest[:12]}'

    # --- cases ---------------------------------------------------------------

    def cases(self) -> tuple[Eval.LocalCase, ...]:
        samples = self.load_samples()
        held_out = sum(1 for item in samples if item.section == 'held_out')
        learning = sum(
            1 for item in samples if item.expected is PlanningIntentKind.LEARNING
        )
        return (
            Eval.LocalCase(
                name=self.ACCURACY_CASE,
                tags=('accuracy', 'held-out'),
                input=f'{held_out} labeled pt-BR held-out intents',
                expected={'min_accuracy': self.HELD_OUT_ACCURACY},
            ),
            Eval.LocalCase(
                name=self.REFUSAL_CASE,
                tags=('undue-refusal', 'learning'),
                input=f'{learning} labeled pt-BR learning intents',
                expected={'max_undue_refusals': 0},
            ),
        )

    def load_samples(self) -> tuple[Sample, ...]:
        evaluation = self.resources.intent_evaluation
        return tuple(
            self.Sample(
                section=section,
                text=item.text,
                expected=PlanningIntentKind(item.label),
            )
            for section in self.SECTIONS
            for item in getattr(evaluation, section)
        )

    # --- execution -----------------------------------------------------------

    def run_local_cases(self, selected: tuple[Any, ...]) -> list[dict[str, Any]]:
        # One pass over the whole set serves every gate.
        started = monotonic()
        try:
            self.samples = self.classify_samples()
        except Exception:  # noqa: BLE001 - provider errors can contain intent text.
            self.samples = None
        duration = monotonic() - started
        reports: list[dict[str, Any]] = []
        for case in selected:
            outcome = (
                self.CaseOutcome(
                    passed=False, failure_code=self.unavailable_failure_code, metrics={}
                )
                if self.samples is None
                else self.score(case.name, self.samples)
            )
            reports.append(
                self.local_case_report(case.name, outcome, duration=duration)
            )
        return reports

    def classify_samples(self) -> tuple[Sample, ...]:
        samples = self.load_samples()
        with self._client(samples) as client:
            use_case = ClassifyPlanningIntentUseCase(self._classifier(client))

            def classify(item: ClassifyPlanningIntentEval.Sample) -> Any:
                return use_case.execute(PlanningQuery(intent=item.text))

            with ThreadPoolExecutor(self.WORKERS) as pool:
                results = tuple(pool.map(classify, samples))
        return tuple(
            self.Sample(
                section=item.section,
                text=item.text,
                expected=item.expected,
                actual=result.kind,
                confidence=round(result.confidence, 3),
            )
            for item, result in zip(samples, results, strict=True)
        )

    def _client(self, samples: tuple[Sample, ...]) -> httpx.Client:
        if not self.double:
            return httpx.Client()
        labels = {item.text: item.expected.value for item in samples}

        def respond(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            choice = labels[payload['state']['intent']]
            rest = (1 - self.DOUBLE_CONFIDENCE) / 2
            return httpx.Response(
                200,
                json={
                    'answers': {
                        JevPlanningIntentClassifierProvider.QUESTION: {
                            'type': 'choice',
                            'choice': choice,
                            'confidence': self.DOUBLE_CONFIDENCE,
                            'probabilities': {
                                kind.value: (
                                    self.DOUBLE_CONFIDENCE
                                    if kind.value == choice
                                    else rest
                                )
                                for kind in PlanningIntentKind
                            },
                        }
                    }
                },
            )

        return httpx.Client(transport=httpx.MockTransport(respond))

    def _classifier(self, client: httpx.Client) -> JevPlanningIntentClassifierProvider:
        settings = get_settings()
        return JevPlanningIntentClassifierProvider(
            client,
            'synthetic-key' if self.double else settings.openrouter_api_key,
            str(settings.openrouter_decisions_url),
            settings.jev_model,
            self.resources.manifest.intent_thresholds,
        )

    # --- metrics -------------------------------------------------------------

    @staticmethod
    def accuracy(samples: tuple[Sample, ...]) -> dict[str, Any]:
        correct = sum(1 for item in samples if item.actual is item.expected)
        return {
            'support': len(samples),
            'correct': correct,
            'accuracy': round(correct / len(samples), 3) if samples else 0.0,
        }

    @staticmethod
    def undue_refusals(samples: tuple[Sample, ...]) -> tuple[Sample, ...]:
        return tuple(
            item
            for item in samples
            if item.expected is PlanningIntentKind.LEARNING
            and item.actual is PlanningIntentKind.OUT_OF_SCOPE
        )

    def score(self, name: str, samples: tuple[Sample, ...]) -> Eval.CaseOutcome:
        if name == self.REFUSAL_CASE:
            refused = self.undue_refusals(samples)
            passed = not refused
            return self.CaseOutcome(
                passed,
                None if passed else 'classification_gate_not_met',
                {
                    'undue_refusals': len(refused),
                    'refused': [item.text for item in refused],
                },
            )
        held_out = tuple(item for item in samples if item.section == 'held_out')
        metrics = self.accuracy(held_out)
        passed = (
            metrics['support'] > 0 and metrics['accuracy'] >= self.HELD_OUT_ACCURACY
        )
        metrics['misclassified'] = self.misclassified(held_out)
        return self.CaseOutcome(
            passed, None if passed else 'classification_gate_not_met', metrics
        )

    @staticmethod
    def misclassified(samples: tuple[Sample, ...]) -> list[dict[str, Any]]:
        return [
            {
                'text': item.text,
                'expected': item.expected.value,
                'actual': item.actual.value if item.actual else None,
                'confidence': item.confidence,
            }
            for item in samples
            if item.actual is not item.expected
        ]

    def report_extras(self) -> dict[str, Any]:
        if self.samples is None:
            return {}
        return {
            'per_section': {
                section: {
                    **self.accuracy(
                        tuple(item for item in self.samples if item.section == section)
                    ),
                    'confusion_matrix': self.confusion_matrix(
                        tuple(item for item in self.samples if item.section == section)
                    ),
                }
                for section in self.SECTIONS
            },
            'calibration_misclassified': self.misclassified(
                tuple(item for item in self.samples if item.section == 'calibration')
            ),
        }

    @staticmethod
    def confusion_matrix(samples: tuple[Sample, ...]) -> dict[str, dict[str, int]]:
        """Rows are the expected kind, columns the predicted kind."""
        counts = Counter(
            (item.expected.value, item.actual.value if item.actual else 'none')
            for item in samples
        )
        kinds = [kind.value for kind in PlanningIntentKind]
        return {
            expected: {predicted: counts[expected, predicted] for predicted in kinds}
            for expected in kinds
        }

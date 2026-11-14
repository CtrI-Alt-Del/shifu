from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib.resources import files
import json
import math
from time import monotonic
from typing import TYPE_CHECKING, Any, ClassVar

from shifu.intelligence.ai.data.mentor_resources import MentorResources
from shifu.intelligence.core.domain.enums.mentor_intent import MentorIntent
from shifu.intelligence.core.domain.structures.mentor_embedding_match import (
    MentorEmbeddingMatch,
)
from shifu.intelligence.prepare_mentor_indexes import prepare_indexes
from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
    SentenceTransformersEmbeddingsProvider,
)
from shifu.intelligence.providers.intent_classification.embeddings.embeddings_mentor_intent_classifier_provider import (
    EmbeddingsMentorIntentClassifierProvider,
)

from evals.eval import Eval

if TYPE_CHECKING:
    from shifu.intelligence.core.domain.structures.mentor_indexed_embedding import (
        MentorIndexedEmbedding,
    )
    from shifu.shared.core.domain.structures.mentor_catalog_entry import (
        MentorCatalogEntry,
    )


class InMemoryMentorEmbeddingsRepository:
    """The `find_nearest` of the database repository, over vectors held in memory.

    Same contract as `SqlalchemyMentorEmbeddingsRepository`: an unknown or inactive
    version is unavailable, an empty eligibility list matches nothing, only the
    requested corpus and eligible references are ranked, similarity is
    `1 - cosine distance`, and ties break by reference then variation key.
    """

    def __init__(self) -> None:
        self._versions: dict[str, tuple[MentorIndexedEmbedding, ...]] = {}
        self._active: str | None = None

    def prepare_version(
        self, version: str, vectors: tuple[MentorIndexedEmbedding, ...]
    ) -> None:
        if not version or not vectors:
            message = 'Index version and complete corpus required'
            raise ValueError(message)
        self._versions[version] = vectors

    def activate_version(self, version: str) -> None:
        vectors = self._versions[version]
        if not {'intents', 'answers'}.issubset({item.corpus for item in vectors}):
            message = 'The index needs the intents and answers corpora'
            raise ValueError(message)
        self._active = version

    def find_nearest(
        self,
        corpus: str,
        version: str,
        query: tuple[float, ...],
        eligible_references: tuple[str, ...],
    ) -> tuple[MentorEmbeddingMatch, ...]:
        if self._active != version:
            message = 'The Mentor index version is not active'
            raise ValueError(message)
        eligible = set(eligible_references)
        ranked = sorted(
            (
                (self._cosine_distance(query, item.vector), item)
                for item in self._versions[version]
                if item.corpus == corpus and item.reference_id in eligible
            ),
            key=lambda row: (row[0], row[1].reference_id, row[1].variation_key),
        )
        return tuple(
            MentorEmbeddingMatch(
                reference_id=item.reference_id,
                variation_key=item.variation_key,
                similarity=1.0 - distance,
            )
            for distance, item in ranked
        )

    @staticmethod
    def _cosine_distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        norms = math.sqrt(sum(a * a for a in left)) * math.sqrt(
            sum(b * b for b in right)
        )
        return 1.0 - dot / norms


class _EmptyMentorCatalogProvider:
    """The intent corpus does not depend on the Curriculum catalog."""

    def read_projection(self) -> tuple[MentorCatalogEntry, ...]:
        return ()

    def is_diagnostic_activity(
        self, skill_id: str, competency_id: str | None, activity_id: str
    ) -> bool:
        return False

    def search(
        self, account_id: str, query: str, eligible_references: tuple[str, ...]
    ) -> tuple[MentorCatalogEntry, ...]:
        return ()


class ClassifyMentorIntentEval(Eval):
    """Gate the local E5 intent classifier on the versioned synthetic pt-BR cases.

    Embeds the intent corpus and every case with the pinned local E5 model in
    process, indexes the corpus through `prepare_indexes` into an in-memory
    repository, and runs the real `EmbeddingsMentorIntentClassifierProvider` with the
    manifest thresholds. That provider also requires lexical evidence of an explicit
    request for `add_skill` and `remove_skill`, because embedding similarity alone
    cannot tell them from near-misses; the report keeps the raw similarity margins.
    No database and no remote model: identical in double and real modes.
    """

    selector = 'classify-mentor-intent'
    workflow_id = 'intelligence-classify-mentor-intent'
    prompt_revision = 'e5-small-max-cosine-v1'
    unavailable_failure_code = 'classifier_unavailable'
    PRECISION: ClassVar[float] = 0.90
    RECALL: ClassVar[float] = 0.70
    HARD_NEGATIVE_FALSE_POSITIVE_RATE: ClassVar[float] = 0.05
    OUT_OF_DOMAIN_FALSE_POSITIVE_RATE: ClassVar[float] = 0.05
    ACTION_INTENTS: ClassVar[tuple[str, ...]] = (
        MentorIntent.ADD_SKILL.value,
        MentorIntent.REMOVE_SKILL.value,
    )
    # Sections of `mentor-evaluation.json`: the intents each one is authoritative for
    # and whether its negatives gate precision. A single-label held-out sentence cannot
    # prove another label wrong (the classifier is multi-label with independent
    # gates), so the existing-intent held-out set gates recall and only reports precision.
    SECTIONS: ClassVar[dict[str, tuple[tuple[str, ...], bool]]] = {
        'intent_calibration': (tuple(intent.value for intent in MentorIntent), True),
        'intent_held_out': (tuple(intent.value for intent in MentorIntent), False),
        'action_intent_calibration': (ACTION_INTENTS, True),
        'action_intent_held_out': (ACTION_INTENTS, True),
    }
    HARD_NEGATIVE_CASE: ClassVar[str] = 'action_intents_hard_negative_false_positive'
    OUT_OF_DOMAIN_CASE: ClassVar[str] = 'out_of_domain_false_positive_rate'
    LEAKAGE_CASE: ClassVar[str] = 'cases_absent_from_intent_corpus'
    # Questions about the feature itself ("serve adicionar Habilidades ao Objetivo?")
    # read like requests to the embedding and to the lexical check. They are measured
    # and reported as a known limitation; the Core still needs a resolved Skill and the
    # learner's button before anything changes.
    META_QUESTION_GROUP: ClassVar[str] = 'meta_question'

    @dataclass(frozen=True)
    class Sample:
        section: str
        text: str
        expected: frozenset[str]
        group: str
        scope: tuple[str, ...]
        precision_gated: bool
        actual: frozenset[str] = frozenset()
        scores: tuple[tuple[str, float], ...] = ()

    def __init__(self, *, mode: str) -> None:
        super().__init__(mode=mode)
        self.model_profile = 'local-e5-small-cosine'
        self.samples: tuple[ClassifyMentorIntentEval.Sample, ...] | None = None
        self.leaked: tuple[str, ...] = ()

    @property
    def dataset_revision(self) -> str:
        sections = self.evaluation()
        digest = hashlib.sha256(
            json.dumps(
                {name: sections[name] for name in self.SECTIONS},
                sort_keys=True,
                ensure_ascii=False,
                separators=(',', ':'),
            ).encode()
        ).hexdigest()
        return f'mentor-intents-synthetic-{digest[:12]}'

    @staticmethod
    def evaluation() -> dict[str, Any]:
        package = files('shifu.intelligence.ai.data')
        return json.loads(
            package.joinpath('mentor-evaluation.json').read_text(encoding='utf-8')
        )

    # --- cases ---------------------------------------------------------------

    def cases(self) -> tuple[Eval.LocalCase, ...]:
        samples = self.load_samples()
        intent_cases = tuple(
            Eval.LocalCase(
                name=f'{intent.value}_precision_recall',
                tags=('precision-recall', intent.value),
                input=(
                    f'{sum(1 for item in samples if intent.value in item.scope)} '
                    'synthetic pt-BR sentences'
                ),
                expected={'min_precision': self.PRECISION, 'min_recall': self.RECALL},
            )
            for intent in MentorIntent
        )
        hard_negatives = sum(1 for item in samples if item.group == 'hard_negative')
        out_of_domain = sum(1 for item in self.out_of_domain(samples))
        return (
            *intent_cases,
            Eval.LocalCase(
                name=self.HARD_NEGATIVE_CASE,
                tags=('false-positive', 'hard-negative', *self.ACTION_INTENTS),
                input=f'{hard_negatives} synthetic pt-BR hard negatives',
                expected={
                    'max_false_positive_rate': self.HARD_NEGATIVE_FALSE_POSITIVE_RATE
                },
            ),
            Eval.LocalCase(
                name=self.OUT_OF_DOMAIN_CASE,
                tags=('false-positive', 'out-of-domain'),
                input=f'{out_of_domain} synthetic pt-BR out-of-domain sentences',
                expected={
                    'max_false_positive_rate': self.OUT_OF_DOMAIN_FALSE_POSITIVE_RATE
                },
            ),
            Eval.LocalCase(
                name=self.LEAKAGE_CASE,
                tags=('dataset-integrity',),
                input=f'{len(samples)} synthetic pt-BR sentences',
                expected={'max_corpus_examples': 0},
            ),
        )

    def load_samples(self) -> tuple[Sample, ...]:
        evaluation = self.evaluation()
        return tuple(
            self.Sample(
                section=section,
                text=entry['text'],
                expected=frozenset(entry['intents']),
                group=entry.get(
                    'group', 'positive' if entry['intents'] else 'negative'
                ),
                scope=scope,
                precision_gated=gated,
            )
            for section, (scope, gated) in self.SECTIONS.items()
            for entry in evaluation[section]
        )

    @staticmethod
    def out_of_domain(
        samples: tuple[Sample, ...], *, gated: bool = True
    ) -> tuple[Sample, ...]:
        return tuple(
            item
            for item in samples
            if item.group == 'negative'
            and len(item.scope) > 2
            and item.precision_gated is gated
        )

    # --- execution -----------------------------------------------------------

    def run_local_cases(self, selected: tuple[Any, ...]) -> list[dict[str, Any]]:
        # One pass over the whole set serves every gate.
        started = monotonic()
        try:
            self.samples = self.classify_samples()
        except Exception:  # noqa: BLE001 - provider errors can contain sentence text.
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
        resources = MentorResources()
        embeddings = SentenceTransformersEmbeddingsProvider()
        repository = InMemoryMentorEmbeddingsRepository()
        prepare_indexes(
            embeddings, repository, _EmptyMentorCatalogProvider(), resources
        )
        classifier = EmbeddingsMentorIntentClassifierProvider(repository, resources)
        samples = self.load_samples()
        corpus = {
            text.strip().casefold()
            for examples in resources.intents.values()
            for text in examples
        }
        self.leaked = tuple(
            item.text for item in samples if item.text.strip().casefold() in corpus
        )
        vectors = embeddings.embed_queries(tuple(item.text for item in samples))
        labels = tuple(resources.intents)
        classified: list[ClassifyMentorIntentEval.Sample] = []
        for item, vector in zip(samples, vectors, strict=True):
            matches = classifier.classify(vector, item.text)
            nearest = repository.find_nearest(
                'intents', resources.version, vector, labels
            )
            best = {
                label: max(
                    (
                        match.similarity
                        for match in nearest
                        if match.reference_id == label
                    ),
                    default=-1.0,
                )
                for label in labels
            }
            classified.append(
                self.Sample(
                    section=item.section,
                    text=item.text,
                    expected=item.expected,
                    group=item.group,
                    scope=item.scope,
                    precision_gated=item.precision_gated,
                    actual=frozenset(match.intent.value for match in matches),
                    scores=tuple((label, round(best[label], 5)) for label in labels),
                )
            )
        return tuple(classified)

    # --- metrics -------------------------------------------------------------

    @classmethod
    def intent_metrics(cls, intent: str, samples: tuple[Sample, ...]) -> dict[str, Any]:
        scoped = tuple(
            item
            for item in samples
            if intent in item.scope and item.group != cls.META_QUESTION_GROUP
        )
        true_positive = sum(
            1 for item in scoped if intent in item.expected and intent in item.actual
        )
        false_positive = sum(
            1
            for item in scoped
            if intent not in item.expected and intent in item.actual
        )
        false_negative = sum(
            1
            for item in scoped
            if intent in item.expected and intent not in item.actual
        )
        support = true_positive + false_negative
        predicted = true_positive + false_positive
        return {
            'support': support,
            'true_positive': true_positive,
            'false_positive': false_positive,
            'false_negative': false_negative,
            'precision': round(true_positive / predicted, 3) if predicted else 0.0,
            'recall': round(true_positive / support, 3) if support else 0.0,
        }

    def false_positive_rate(
        self, items: tuple[Sample, ...], intents: tuple[str, ...]
    ) -> dict[str, Any]:
        triggered = tuple(item for item in items if item.actual.intersection(intents))
        return {
            'support': len(items),
            'false_positive': len(triggered),
            'false_positive_rate': (
                round(len(triggered) / len(items), 3) if items else 1.0
            ),
            'misclassified': [
                {
                    'text': item.text,
                    'actual': sorted(item.actual.intersection(intents)),
                }
                for item in triggered
            ],
        }

    def score(self, name: str, samples: tuple[Sample, ...]) -> Eval.CaseOutcome:
        if name == self.LEAKAGE_CASE:
            passed = not self.leaked
            return self.CaseOutcome(
                passed,
                None if passed else 'case_text_in_intent_corpus',
                {'corpus_examples_in_cases': list(self.leaked)},
            )
        if name in {self.HARD_NEGATIVE_CASE, self.OUT_OF_DOMAIN_CASE}:
            hard = name == self.HARD_NEGATIVE_CASE
            items = (
                tuple(item for item in samples if item.group == 'hard_negative')
                if hard
                else self.out_of_domain(samples)
            )
            metrics = self.false_positive_rate(
                items, self.ACTION_INTENTS if hard else tuple(self.every_intent())
            )
            limit = (
                self.HARD_NEGATIVE_FALSE_POSITIVE_RATE
                if hard
                else self.OUT_OF_DOMAIN_FALSE_POSITIVE_RATE
            )
            passed = metrics['support'] > 0 and metrics['false_positive_rate'] <= limit
            return self.CaseOutcome(
                passed, None if passed else 'classification_gate_not_met', metrics
            )
        intent = name.removesuffix('_precision_recall')
        metrics = self.intent_metrics(intent, samples)
        gated = self.intent_metrics(
            intent, tuple(item for item in samples if item.precision_gated)
        )
        metrics['gated_precision'] = gated['precision']
        metrics['gated_false_positive'] = gated['false_positive']
        passed = (
            metrics['support'] > 0
            and gated['precision'] >= self.PRECISION
            and metrics['recall'] >= self.RECALL
        )
        metrics['misclassified'] = [
            {
                'text': item.text,
                'section': item.section,
                'expected': sorted(item.expected.intersection({intent})),
                'actual': sorted(item.actual.intersection({intent})),
            }
            for item in samples
            if intent in item.scope
            and item.group != self.META_QUESTION_GROUP
            and (intent in item.expected) != (intent in item.actual)
        ]
        return self.CaseOutcome(
            passed, None if passed else 'classification_gate_not_met', metrics
        )

    @staticmethod
    def every_intent() -> tuple[str, ...]:
        return tuple(intent.value for intent in MentorIntent)

    def report_extras(self) -> dict[str, Any]:
        if self.samples is None:
            return {}
        partitions: dict[str, dict[str, Any]] = {}
        for intent in self.every_intent():
            partitions[intent] = {
                section: self.intent_metrics(
                    intent,
                    tuple(item for item in self.samples if item.section == section),
                )
                for section in self.SECTIONS
                if intent in self.SECTIONS[section][0]
            }
        return {
            'per_intent': {
                intent: self.intent_metrics(intent, self.samples)
                for intent in self.every_intent()
            },
            'per_intent_by_section': partitions,
            'out_of_domain_not_gated': self.false_positive_rate(
                self.out_of_domain(self.samples, gated=False),
                self.every_intent(),
            ),
            'known_limitation_meta_questions': self.false_positive_rate(
                tuple(
                    item
                    for item in self.samples
                    if item.group == self.META_QUESTION_GROUP
                ),
                self.ACTION_INTENTS,
            ),
            'action_intent_scores': {
                intent: self.score_margins(intent, self.samples)
                for intent in self.ACTION_INTENTS
            },
        }

    @staticmethod
    def score_margins(intent: str, samples: tuple[Sample, ...]) -> dict[str, Any]:
        """Lowest positive and highest negative raw similarity: the threshold margin."""
        positives = [
            dict(item.scores)[intent]
            for item in samples
            if intent in item.scope and intent in item.expected
        ]
        negatives = [
            dict(item.scores)[intent]
            for item in samples
            if intent in item.scope and intent not in item.expected
        ]
        return {
            'lowest_positive': min(positives, default=None),
            'highest_negative': max(negatives, default=None),
        }

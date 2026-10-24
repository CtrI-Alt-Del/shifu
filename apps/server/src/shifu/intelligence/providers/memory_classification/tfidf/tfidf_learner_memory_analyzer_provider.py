import re
from collections import Counter
from dataclasses import dataclass
from threading import Lock
from typing import TYPE_CHECKING, ClassVar, cast

from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.metrics.pairwise import (
    cosine_similarity,  # pyright: ignore[reportUnknownVariableType] - scikit-learn ships no complete stubs.
)

from shifu.intelligence.ai.data.learner_memory_resources import LearnerMemoryResources
from shifu.intelligence.core.domain.enums.learner_memory_category import (
    LearnerMemoryCategory,
)
from shifu.intelligence.core.domain.structures.learner_memory_analysis import (
    LearnerMemoryAnalysis,
)
from shifu.intelligence.core.domain.structures.learner_memory_concept import (
    LearnerMemoryConcept,
)
from shifu.intelligence.core.domain.structures.learner_memory_statement import (
    LearnerMemoryStatement,
)
from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
    SpacyMentorTextPreprocessorProvider,
)

if TYPE_CHECKING:
    from scipy.sparse import csr_matrix

_NO_MEMORY = 'nenhuma'


@dataclass(frozen=True, slots=True)
class _Model:
    vectorizer: CountVectorizer
    transformer: TfidfTransformer
    matrix: 'csr_matrix'
    labels: tuple[str, ...]


class TfidfLearnerMemoryAnalyzerProvider:
    """White-box learner statement classifier: count BoW, TF-IDF and 3-nearest vote.

    spaCy filters the eligible sentences. The TF-IDF model is fitted once, lazily and
    under a lock, on the versioned synthetic examples only; learner text is only
    transformed, and ``concepts`` never triggers the fit.
    """

    MAX_CONTENT_CODE_POINTS: ClassVar[int] = 280
    _LEADING_SEPARATORS: ClassVar[str] = r'[\s,;:\-]*'

    _preprocessor: SpacyMentorTextPreprocessorProvider
    _resources: LearnerMemoryResources
    _connectors: re.Pattern[str] | None
    _lock: Lock
    _model: _Model | None

    def __init__(
        self,
        preprocessor: SpacyMentorTextPreprocessorProvider,
        resources: LearnerMemoryResources,
    ) -> None:
        self._preprocessor = preprocessor
        self._resources = resources
        self._lock = Lock()
        self._model = None
        connectors = sorted(
            {connector.strip() for connector in resources.manifest.connectors},
            key=lambda connector: (-len(connector), connector),
        )
        self._connectors = (
            re.compile(
                r'^(?:'
                + '|'.join(re.escape(connector) for connector in connectors)
                + r')(?=[\s,;:.!\-]|$)'
                + self._LEADING_SEPARATORS,
                re.IGNORECASE,
            )
            if connectors
            else None
        )

    def analyze(self, text: str) -> LearnerMemoryAnalysis:
        sentences = self._preprocessor.learner_sentences(
            text, self._resources.cue_words
        )
        statements: list[LearnerMemoryStatement] = []
        for sentence in sentences:
            if not sentence.is_eligible:
                continue
            category = self._classify(sentence.tokens)
            if category is None:
                continue
            content = self._clean(sentence.text)
            if not 1 <= len(content) <= self.MAX_CONTENT_CODE_POINTS:
                continue
            statements.append(
                LearnerMemoryStatement(
                    category=category, content=content, concepts=sentence.concepts
                )
            )
        return LearnerMemoryAnalysis(
            statements=tuple(statements), sentence_count=len(sentences)
        )

    def concepts(self, content: str) -> tuple[LearnerMemoryConcept, ...]:
        return self._preprocessor.learner_concepts(content, self._resources.cue_words)

    def _classify(self, tokens: tuple[str, ...]) -> LearnerMemoryCategory | None:
        if not tokens:
            return None
        model = self._fitted()
        vector = model.vectorizer.transform([' '.join(tokens)])  # pyright: ignore[reportUnknownMemberType] - scikit-learn ships no complete stubs.
        query = cast(
            'csr_matrix',
            model.transformer.transform(vector),  # pyright: ignore[reportUnknownMemberType] - scikit-learn ships no complete stubs.
        )
        scores = cast(
            'list[float]',
            cosine_similarity(query, model.matrix)[0].tolist(),  # pyright: ignore[reportUnknownMemberType] - scikit-learn ships no complete stubs.
        )
        ranked = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
        nearest = ranked[: self._resources.manifest.k]
        if scores[nearest[0]] < self._resources.manifest.minimum_similarity:
            return None
        votes = Counter(model.labels[index] for index in nearest)
        winner, count = votes.most_common(1)[0]
        if count < 2:
            # No majority: the class of the single most similar example wins.
            winner = model.labels[nearest[0]]
        if winner == _NO_MEMORY:
            return None
        return LearnerMemoryCategory(winner)

    def _fitted(self) -> _Model:
        with self._lock:
            if self._model is None:
                self._model = self._fit()
            return self._model

    def _fit(self) -> _Model:
        examples = self._resources.examples
        documents = [
            ' '.join(self._preprocessor.classification_tokens(example.text))
            for example in examples
        ]
        # Tokens are already lemmatized and normalized: split on whitespace only.
        vectorizer = CountVectorizer(
            ngram_range=(1, 2),
            tokenizer=str.split,
            token_pattern=None,  # pyright: ignore[reportArgumentType] - scikit-learn types the pattern as str; None disables it when a tokenizer is given.
            lowercase=False,
        )
        counts = cast(
            'csr_matrix',
            vectorizer.fit_transform(documents),  # pyright: ignore[reportUnknownMemberType] - scikit-learn ships no complete stubs.
        )
        transformer = TfidfTransformer(norm='l2', smooth_idf=True)
        matrix = cast(
            'csr_matrix',
            transformer.fit_transform(counts),  # pyright: ignore[reportUnknownMemberType] - scikit-learn ships no complete stubs.
        )
        return _Model(
            vectorizer=vectorizer,
            transformer=transformer,
            matrix=matrix,
            labels=tuple(example.label for example in examples),
        )

    def _clean(self, sentence: str) -> str:
        content = sentence.strip()
        while self._connectors is not None:
            stripped = self._connectors.sub('', content, count=1)
            if stripped == content:
                break
            content = stripped
        content = content.strip()
        return content[:1].upper() + content[1:]

from collections import Counter
from math import sqrt

from shifu.intelligence.ai.data.learner_memory_resources import LearnerMemoryResources
from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
    SpacyMentorTextPreprocessorProvider,
)


class BagOfWordsLearnerMemorySimilarityProvider:
    """Count bag-of-words cosine over subject terms; the lexicon is the two texts'."""

    _preprocessor: SpacyMentorTextPreprocessorProvider
    _cue_words: frozenset[str]

    def __init__(
        self,
        preprocessor: SpacyMentorTextPreprocessorProvider,
        resources: LearnerMemoryResources,
    ) -> None:
        self._preprocessor = preprocessor
        self._cue_words = resources.cue_words

    def similarity(self, left: str, right: str) -> float:
        left_counts = Counter(self._preprocessor.subject_terms(left, self._cue_words))
        right_counts = Counter(self._preprocessor.subject_terms(right, self._cue_words))
        lexicon = left_counts.keys() | right_counts.keys()
        dot = sum(left_counts[term] * right_counts[term] for term in lexicon)
        norm = sqrt(sum(value * value for value in left_counts.values())) * sqrt(
            sum(value * value for value in right_counts.values())
        )
        if norm == 0:
            return 0.0
        return min(1.0, max(0.0, dot / norm))

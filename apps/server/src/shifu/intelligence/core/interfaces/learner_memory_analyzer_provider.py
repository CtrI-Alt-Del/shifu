from typing import Protocol

from shifu.intelligence.core.domain.structures import (
    LearnerMemoryAnalysis,
    LearnerMemoryConcept,
)


class LearnerMemoryAnalyzerProvider(Protocol):
    def analyze(self, text: str) -> LearnerMemoryAnalysis:
        """Classify the eligible sentences of one learner message."""
        ...

    def concepts(self, content: str) -> tuple[LearnerMemoryConcept, ...]:
        """Extract up to three concepts without fitting any classifier (edit path)."""
        ...

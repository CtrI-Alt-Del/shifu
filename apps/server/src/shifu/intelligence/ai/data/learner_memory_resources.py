import hashlib
import json
import re
import unicodedata
from importlib.resources import files
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from shifu.intelligence.core.domain.enums.learner_memory_category import (
    LearnerMemoryCategory,
)

type LearnerMemoryLabel = Literal[
    'explanation_preference',
    'declared_knowledge',
    'interest_or_intention',
    'recurring_difficulty',
    'nenhuma',
]


class _Strict(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid', strict=True, frozen=True
    )


class _Provenance(_Strict):
    source: str = Field(min_length=1)
    language: Literal['pt-BR']
    contains_real_learner_data: Literal[False]


class LearnerMemoryExample(_Strict):
    text: str = Field(min_length=1)
    label: LearnerMemoryLabel


class LearnerMemoryEvaluationCase(_Strict):
    text: str = Field(min_length=1)
    label: LearnerMemoryLabel
    tags: list[str]


class _ExamplesFile(_Strict):
    provenance: _Provenance
    examples_version: str = Field(min_length=1)
    examples: list[LearnerMemoryExample]


class _EvaluationFile(_Strict):
    provenance: _Provenance
    dataset_revision: str = Field(min_length=1)
    cases: list[LearnerMemoryEvaluationCase]


class LearnerMemoryManifest(_Strict):
    format_version: int
    examples_version: str = Field(min_length=1)
    preprocessor: str
    preprocessor_version: str
    k: int = Field(ge=1)
    minimum_similarity: float = Field(ge=0, le=1)
    update_threshold: float = Field(gt=0, le=1)
    relevance_threshold: float = Field(gt=0, le=1)
    connectors: list[str]
    cue_words: list[str]


def normalize_learner_text(value: str) -> str:
    """Casefold, strip accents and collapse whitespace and punctuation."""
    decomposed = unicodedata.normalize('NFKD', value.casefold())
    stripped = ''.join(char for char in decomposed if not unicodedata.combining(char))
    return ' '.join(re.sub(r'[^\w]+', ' ', stripped).split())


class LearnerMemoryResources:
    """Versioned synthetic examples, evaluation set and manifest of the classifier."""

    FORMAT_VERSION: ClassVar[int] = 1
    EXAMPLE_FILE: ClassVar[str] = 'mentor-memory-examples.json'
    EVALUATION_FILE: ClassVar[str] = 'mentor-memory-evaluation.json'
    MANIFEST_FILE: ClassVar[str] = 'mentor-memory-manifest.json'

    examples: tuple[LearnerMemoryExample, ...]
    evaluation: tuple[LearnerMemoryEvaluationCase, ...]
    dataset_revision: str
    manifest: LearnerMemoryManifest
    cue_words: frozenset[str]
    version: str

    def __init__(self) -> None:
        package = files('shifu.intelligence.ai.data')
        names = (self.EXAMPLE_FILE, self.EVALUATION_FILE, self.MANIFEST_FILE)
        raw = {
            name: package.joinpath(name).read_text(encoding='utf-8') for name in names
        }
        examples_file = _ExamplesFile.model_validate_json(raw[names[0]])
        evaluation_file = _EvaluationFile.model_validate_json(raw[names[1]])
        self.manifest = LearnerMemoryManifest.model_validate_json(raw[names[2]])
        self.examples = tuple(examples_file.examples)
        self.evaluation = tuple(evaluation_file.cases)
        self.dataset_revision = evaluation_file.dataset_revision
        self._validate(examples_file.examples_version)
        self.cue_words = frozenset(
            normalize_learner_text(word) for word in self.manifest.cue_words
        )
        canonical = json.dumps(
            {name: json.loads(text) for name, text in raw.items()},
            sort_keys=True,
            ensure_ascii=False,
            separators=(',', ':'),
        )
        self.version = hashlib.sha256(canonical.encode()).hexdigest()

    def _validate(self, examples_version: str) -> None:
        manifest = self.manifest
        if (
            manifest.format_version != self.FORMAT_VERSION
            or manifest.examples_version != examples_version
            or manifest.preprocessor != 'pt_core_news_sm'
            or manifest.preprocessor_version != '3.8.0'
            or manifest.k != 3
            or any(not word.strip() for word in manifest.connectors)
            or any(not word.strip() for word in manifest.cue_words)
        ):
            raise ValueError('Incompatible learner memory configuration')
        labels = {category.value for category in LearnerMemoryCategory} | {'nenhuma'}
        for dataset in (self.examples, self.evaluation):
            if {item.label for item in dataset} != labels:
                raise ValueError('Incomplete learner memory dataset')
        normalized_examples = [
            normalize_learner_text(example.text) for example in self.examples
        ]
        if len(set(normalized_examples)) != len(normalized_examples):
            raise ValueError('Duplicate learner memory example')
        # The evaluation must measure generalization, never memorization.
        if set(normalized_examples) & {
            normalize_learner_text(case.text) for case in self.evaluation
        }:
            raise ValueError('Learner memory evaluation overlaps the training examples')

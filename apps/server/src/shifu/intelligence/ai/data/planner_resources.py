import hashlib
import json
from dataclasses import asdict
from importlib.resources import files
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from shifu.intelligence.core.domain.enums.planning_intent_kind import (
    PlanningIntentKind,
)
from shifu.shared.core.domain.structures.skill_catalog_entry import SkillCatalogEntry


class _LabeledIntent(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid', strict=True, frozen=True
    )
    text: str = Field(min_length=1)
    label: PlanningIntentKind


class _IntentEvaluation(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid', strict=True, frozen=True
    )
    calibration: list[_LabeledIntent]
    held_out: list[_LabeledIntent]


class _RetrievalQuery(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid', strict=True, frozen=True
    )
    id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    answers: list[str]
    relevant: list[str]


class _RetrievalEvaluation(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid', strict=True, frozen=True
    )
    queries: list[_RetrievalQuery]


class _Manifest(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid', strict=True, frozen=True
    )
    format_version: int
    model: str
    model_revision: str
    dimension: int
    normalized: bool
    query_prefix: str
    passage_prefix: str
    preprocessor: str
    preprocessor_version: str
    negation: list[str]
    rrf_k: int = Field(gt=0)
    lexical_limit: int = Field(gt=0, le=10)
    semantic_limit: int = Field(gt=0, le=10)
    candidate_limit: int = Field(gt=0, le=20)
    classifier_model: str
    intent_thresholds: dict[str, float]
    calibration_status: str


def _read_resource(name: str) -> str:
    return (
        files('shifu.intelligence.ai.data').joinpath(name).read_text(encoding='utf-8')
    )


class PlannerResources:
    """Versioned manifest and labeled sets of the Planner NLP capabilities."""

    manifest: _Manifest
    intent_evaluation: _IntentEvaluation
    retrieval_evaluation: _RetrievalEvaluation
    version: str

    def __init__(self) -> None:
        names = (
            'planner-index-manifest.json',
            'planner-intent-evaluation.json',
            'planner-retrieval-evaluation.json',
        )
        raw = {name: _read_resource(name) for name in names}
        self.manifest = _Manifest.model_validate_json(raw[names[0]])
        self.intent_evaluation = _IntentEvaluation.model_validate_json(raw[names[1]])
        self.retrieval_evaluation = TypeAdapter(_RetrievalEvaluation).validate_json(
            raw[names[2]]
        )
        self._validate()
        canonical = json.dumps(
            {name: json.loads(text) for name, text in raw.items()},
            sort_keys=True,
            ensure_ascii=False,
            separators=(',', ':'),
        )
        self.version = hashlib.sha256(canonical.encode()).hexdigest()

    def bind_catalog(self, skills: tuple[SkillCatalogEntry, ...]) -> None:
        """Tie the index version to the authorized catalog it was prepared from."""
        canonical = json.dumps(
            sorted((asdict(skill) for skill in skills), key=lambda skill: skill['id']),
            sort_keys=True,
            ensure_ascii=False,
            separators=(',', ':'),
        )
        self.version = hashlib.sha256(
            f'{self.version}:{canonical}'.encode()
        ).hexdigest()

    def _validate(self) -> None:
        kinds = {kind.value for kind in PlanningIntentKind}
        if (
            self.manifest.dimension != 384
            or not self.manifest.normalized
            or self.manifest.model != 'intfloat/multilingual-e5-small'
            or self.manifest.query_prefix != 'query: '
            or self.manifest.passage_prefix != 'passage: '
            or self.manifest.preprocessor != 'pt_core_news_sm'
            or set(self.manifest.intent_thresholds) != kinds
            or any(
                not 0 <= threshold <= 1
                for threshold in self.manifest.intent_thresholds.values()
            )
            or not self.manifest.negation
        ):
            raise ValueError('Invalid Planner index manifest')
        if not self.intent_evaluation.held_out or not self.retrieval_evaluation.queries:
            raise ValueError('Planner evaluation sets cannot be empty')

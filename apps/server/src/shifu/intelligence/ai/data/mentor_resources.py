import hashlib
import json
from dataclasses import asdict
from importlib.resources import files
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from shifu.intelligence.core.domain.enums.mentor_intent import MentorIntent
from shifu.shared.core.domain.structures.mentor_catalog_entry import MentorCatalogEntry


class _Answer(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid', strict=True, frozen=True
    )
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    variations: list[str]
    answer: str = Field(min_length=1)
    topics: list[str]


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
    intent_thresholds: dict[str, float]
    faq_cosine_threshold: float = Field(ge=0, le=1)
    faq_margin: float = Field(ge=0, le=1)
    faq_reranker_model: str
    faq_reranker_revision: str
    faq_rerank_document_format: str
    faq_query_policy_version: int
    faq_candidate_cosine_threshold: float = Field(ge=0, le=1)
    faq_rerank_limit: int = Field(ge=2, le=6)
    faq_rerank_score_threshold: float = Field(allow_inf_nan=False)
    faq_rerank_margin: float = Field(gt=0, allow_inf_nan=False)
    faq_tie_limit: int = Field(ge=1, le=3)
    calibration_status: str
    review_thresholds: dict[str, float]


class MentorResources:
    intents: dict[str, list[str]]
    answers: tuple[_Answer, ...]
    manifest: _Manifest
    version: str

    def __init__(self) -> None:
        package = files('shifu.intelligence.ai.data')
        names = (
            'mentor-intents.json',
            'mentor-answers.json',
            'mentor-index-manifest.json',
        )
        raw = {
            name: package.joinpath(name).read_text(encoding='utf-8') for name in names
        }
        self.intents = TypeAdapter(dict[str, list[str]]).validate_json(
            raw[names[0]], strict=True
        )
        self.answers = tuple(TypeAdapter(list[_Answer]).validate_json(raw[names[1]]))
        self.manifest = _Manifest.model_validate_json(raw[names[2]])
        self._validate()
        canonical = json.dumps(
            {name: json.loads(text) for name, text in raw.items()},
            sort_keys=True,
            ensure_ascii=False,
            separators=(',', ':'),
        )
        self.version = hashlib.sha256(canonical.encode()).hexdigest()

    def bind_catalog_version(self, projection: tuple[MentorCatalogEntry, ...]) -> None:
        canonical = json.dumps(
            sorted(
                (asdict(entry) for entry in projection),
                key=lambda entry: json.dumps(entry, sort_keys=True),
            ),
            sort_keys=True,
            ensure_ascii=False,
            separators=(',', ':'),
        )
        self.version = hashlib.sha256(
            f'{self.version}:{canonical}'.encode()
        ).hexdigest()

    def _validate(self) -> None:
        labels = {intent.value for intent in MentorIntent}
        if (
            set(self.intents) != labels
            or set(self.manifest.intent_thresholds) != labels
        ):
            raise ValueError('Incomplete Mentor intent corpus')
        if any(
            not examples or any(not text.strip() for text in examples)
            for examples in self.intents.values()
        ):
            raise ValueError('Empty Mentor intent example')
        if len({answer.id for answer in self.answers}) != len(self.answers):
            raise ValueError('Duplicate Mentor answer ID')
        if any(
            not 0 < threshold <= 1
            for threshold in self.manifest.intent_thresholds.values()
        ):
            raise ValueError('Invalid Mentor intent threshold')
        if (
            self.manifest.dimension != 384
            or not self.manifest.normalized
            or self.manifest.model != 'intfloat/multilingual-e5-small'
            or self.manifest.model_revision
            != '614241f622f53c4eeff9890bdc4f31cfecc418b3'
            or self.manifest.query_prefix != 'query: '
            or self.manifest.passage_prefix != 'passage: '
            or self.manifest.preprocessor != 'pt_core_news_sm'
            or self.manifest.faq_reranker_model
            != 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'
            or self.manifest.faq_reranker_revision
            != '1427fd652930e4ba29e8149678df786c240d8825'
            or self.manifest.faq_rerank_document_format
            != 'question_variations_answer_v1'
            or self.manifest.faq_query_policy_version != 3
        ):
            raise ValueError('Incompatible Mentor index configuration')

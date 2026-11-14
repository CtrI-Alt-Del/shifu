from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from time import monotonic
from typing import TYPE_CHECKING, Any, ClassVar

from shifu.curriculum.database.roadmap_skills_seed import ROADMAP_SKILL_ID_PREFIX
from shifu.intelligence.ai.data.planner_resources import PlannerResources
from shifu.intelligence.core.domain.structures import PlanningQuery
from shifu.intelligence.core.domain.structures.planning_embedding_match import (
    PlanningEmbeddingMatch,
)
from shifu.intelligence.prepare_planning_indexes import prepare_indexes
from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
    SentenceTransformersEmbeddingsProvider,
)
from shifu.intelligence.providers.planning.retrieval.sklearn.tfidf_sentence_transformers_planning_skill_retrieval_provider import (
    TfidfSentenceTransformersPlanningSkillRetrievalProvider,
)
from shifu.intelligence.providers.planning.retrieval.sklearn.tfidf_word2vec_planning_skill_retrieval_provider import (
    TfidfWord2VecPlanningSkillRetrievalProvider,
)
from shifu.intelligence.providers.planning.text_preprocessing.spacy.spacy_planning_text_preprocessor_provider import (
    SpacyPlanningTextPreprocessorProvider,
)
from shifu.intelligence.providers.planning.word_vectors.huggingface.nilc_word2vec_word_vectors_provider import (
    NilcWord2VecWordVectorsProvider,
)
from shifu.shared.core.domain.structures.skill_catalog_entry import SkillCatalogEntry
from shifu.shared.core.domain.structures.skill_catalog_page import SkillCatalogPage
from shifu.shared.database.seed_data import build_development_seed

from evals.eval import Eval

if TYPE_CHECKING:
    from collections.abc import Sequence

    from shifu.intelligence.core.domain.structures.planning_indexed_embedding import (
        PlanningIndexedEmbedding,
    )
    from shifu.shared.core.domain.structures.skill_foundation_entry import (
        SkillFoundationEntry,
    )


class _InMemoryPlanningEmbeddingsRepository:
    """The `find_nearest` of the database repository, over vectors held in memory.

    Same contract as `SqlalchemyPlanningEmbeddingsRepository`: an unknown or inactive
    version is unavailable, only eligible Skills are ranked, similarity is
    `1 - cosine distance`, and ties break by Skill id.
    """

    def __init__(self) -> None:
        self._versions: dict[str, tuple[PlanningIndexedEmbedding, ...]] = {}
        self._active: str | None = None

    def prepare_version(
        self, version: str, vectors: tuple[PlanningIndexedEmbedding, ...]
    ) -> None:
        if not version or not vectors:
            message = 'Index version and complete corpus required'
            raise ValueError(message)
        self._versions[version] = vectors

    def activate_version(self, version: str) -> None:
        if version not in self._versions:
            message = 'Unknown Planner index version'
            raise ValueError(message)
        self._active = version

    def find_active_version(self) -> str | None:
        return self._active

    def find_nearest(
        self,
        version: str,
        query: tuple[float, ...],
        eligible_skill_ids: tuple[str, ...],
        limit: int,
    ) -> tuple[PlanningEmbeddingMatch, ...]:
        if self._active != version:
            message = 'The Planner index version is not active'
            raise ValueError(message)
        eligible = set(eligible_skill_ids)
        ranked = sorted(
            (
                (self._cosine_distance(query, item.vector), item.skill_id)
                for item in self._versions[version]
                if item.skill_id in eligible
            ),
        )
        return tuple(
            PlanningEmbeddingMatch(skill_id=skill_id, similarity=1.0 - distance)
            for distance, skill_id in ranked[: max(limit, 0)]
        )

    @staticmethod
    def _cosine_distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        norms = math.sqrt(sum(a * a for a in left)) * math.sqrt(
            sum(b * b for b in right)
        )
        return 1.0 - dot / norms


class _SeedSkillCatalogProvider:
    """The authorized Skill catalog of the development seed, without a database."""

    def __init__(self, skills: tuple[SkillCatalogEntry, ...]) -> None:
        self._skills = skills

    def search_skills(
        self, *, query: str | None, cursor: str | None, limit: int
    ) -> SkillCatalogPage:
        return SkillCatalogPage(items=self._skills[:limit], next_cursor=None)

    def find_skill_by_id(self, skill_id: str) -> SkillCatalogEntry | None:
        return next((skill for skill in self._skills if skill.id == skill_id), None)

    def list_skills(self) -> tuple[SkillCatalogEntry, ...]:
        return self._skills

    def find_direct_foundations_for_many(
        self, skill_ids: list[str]
    ) -> dict[str, list[SkillFoundationEntry]]:
        return {}


class RetrievePlanningSkillsEval(Eval):
    """Gate the Planner hybrid Skill retrieval on the versioned labeled pt-BR queries.

    Builds the development seed catalog the queries were labeled for (the roadmap
    Skills are placeholder test data and stay out) and ranks every query of
    `planner-retrieval-evaluation.json` with the real TF-IDF + Word2Vec provider, the
    default meaning model, fused by reciprocal rank. Queries with relevant Skills gate
    Recall@10 and MRR; the hybrid MRR may not fall below the lexical one. Queries the
    catalog does not cover must match no term and stay below every covered query in
    top-1 cosine. No database and no remote model: identical in double and real modes.
    """

    selector = 'retrieve-planning-skills'
    workflow_id = 'intelligence-retrieve-planning-skills'
    prompt_revision = 'tfidf-word2vec-nilc-s100-rrf-v1'
    MODEL_PROFILE: ClassVar[str] = 'local-tfidf-word2vec-nilc-s100-rrf'
    unavailable_failure_code = 'retrieval_unavailable'
    RECALL_AT_10: ClassVar[float] = 0.89
    MRR: ClassVar[float] = 0.80
    RECALL_CASE: ClassVar[str] = 'hybrid_recall_at_10'
    MRR_CASE: ClassVar[str] = 'hybrid_mrr'
    NO_COVERAGE_CASE: ClassVar[str] = 'uncovered_queries_separated'

    @dataclass(frozen=True)
    class Ranked:
        id: str
        kind: str
        relevant: frozenset[str]
        lexical: tuple[str, ...]
        semantic: tuple[str, ...]
        hybrid: tuple[str, ...]
        top_similarity: float

    def __init__(self, *, mode: str) -> None:
        super().__init__(mode=mode)
        self.model_profile = self.MODEL_PROFILE
        self.resources = PlannerResources()
        self.ranked: tuple[RetrievePlanningSkillsEval.Ranked, ...] | None = None

    @property
    def dataset_revision(self) -> str:
        evaluation = self.resources.retrieval_evaluation.model_dump()
        digest = hashlib.sha256(
            json.dumps(
                evaluation, sort_keys=True, ensure_ascii=False, separators=(',', ':')
            ).encode()
        ).hexdigest()
        return f'planner-retrieval-synthetic-{digest[:12]}'

    # --- cases ---------------------------------------------------------------

    def cases(self) -> tuple[Eval.LocalCase, ...]:
        queries = self.resources.retrieval_evaluation.queries
        covered = sum(1 for item in queries if item.kind != 'no-coverage')
        uncovered = len(queries) - covered
        return (
            Eval.LocalCase(
                name=self.RECALL_CASE,
                tags=('ranking', 'recall'),
                input=f'{covered} labeled pt-BR queries with relevant Skills',
                expected={'min_recall_at_10': self.RECALL_AT_10},
            ),
            Eval.LocalCase(
                name=self.MRR_CASE,
                tags=('ranking', 'mrr'),
                input=f'{covered} labeled pt-BR queries with relevant Skills',
                expected={'min_mrr': self.MRR, 'min_over_lexical_mrr': 0.0},
            ),
            Eval.LocalCase(
                name=self.NO_COVERAGE_CASE,
                tags=('no-coverage',),
                input=f'{uncovered} labeled pt-BR queries without catalog coverage',
                expected={'lexical_matches': 0, 'below_every_clear_query': True},
            ),
        )

    # --- execution -----------------------------------------------------------

    def run_local_cases(self, selected: tuple[Any, ...]) -> list[dict[str, Any]]:
        # One pass over the whole set serves every gate.
        started = monotonic()
        try:
            self.ranked = self.rank_queries()
        except Exception:  # noqa: BLE001 - provider errors can contain query text.
            self.ranked = None
        duration = monotonic() - started
        reports: list[dict[str, Any]] = []
        for case in selected:
            outcome = (
                self.CaseOutcome(
                    passed=False, failure_code=self.unavailable_failure_code, metrics={}
                )
                if self.ranked is None
                else self.score(case.name, self.ranked)
            )
            reports.append(
                self.local_case_report(case.name, outcome, duration=duration)
            )
        return reports

    def rank_queries(self) -> tuple[Ranked, ...]:
        seed = build_development_seed()
        skills = tuple(
            SkillCatalogEntry(
                id=skill.id, name=skill.name, description=skill.description
            )
            for skill in seed.skills
            if not skill.id.startswith(ROADMAP_SKILL_ID_PREFIX)
        )
        preprocessor = SpacyPlanningTextPreprocessorProvider(
            self.resources.manifest.negation
        )
        provider = TfidfWord2VecPlanningSkillRetrievalProvider(
            skills, NilcWord2VecWordVectorsProvider(), preprocessor, self.resources
        )
        ids_by_name = {skill.name: skill.id for skill in skills}
        ranked: list[RetrievePlanningSkillsEval.Ranked] = []
        for item in self.resources.retrieval_evaluation.queries:
            query = PlanningQuery(intent=item.intent, answers=tuple(item.answers))
            ranking = provider.retrieve(query)
            similarities = provider.similarities(query)
            ranked.append(
                self.ranked_item(
                    item,
                    ids_by_name,
                    ranking,
                    similarities[0][1] if similarities else 0.0,
                )
            )
        return tuple(ranked)

    def ranked_item(
        self,
        item: Any,
        ids_by_name: dict[str, str],
        ranking: Any,
        top_similarity: float,
    ) -> Ranked:
        return self.Ranked(
            id=item.id,
            kind=item.kind,
            relevant=frozenset(ids_by_name[name] for name in item.relevant),
            lexical=ranking.lexical_ranking,
            semantic=ranking.semantic_ranking,
            hybrid=tuple(entry.skill_id for entry in ranking.entries),
            top_similarity=round(top_similarity, 5),
        )

    # --- metrics -------------------------------------------------------------

    @staticmethod
    def ranking_metrics(
        rankings: Sequence[tuple[Sequence[str], frozenset[str]]],
    ) -> dict[str, float]:
        reciprocal = recall_5 = recall_10 = 0.0
        for ranked, relevant in rankings:
            positions = [
                rank for rank, item in enumerate(ranked, 1) if item in relevant
            ]
            reciprocal += 1 / positions[0] if positions else 0.0
            recall_5 += len([rank for rank in positions if rank <= 5]) / len(relevant)
            recall_10 += len([rank for rank in positions if rank <= 10]) / len(relevant)
        count = len(rankings) or 1
        return {
            'mrr': round(reciprocal / count, 4),
            'recall_at_5': round(recall_5 / count, 4),
            'recall_at_10': round(recall_10 / count, 4),
        }

    def per_strategy(self, ranked: tuple[Ranked, ...]) -> dict[str, dict[str, float]]:
        covered = tuple(item for item in ranked if item.kind != 'no-coverage')
        return {
            strategy: self.ranking_metrics(
                [(getattr(item, strategy), item.relevant) for item in covered]
            )
            for strategy in ('lexical', 'semantic', 'hybrid')
        }

    def score(self, name: str, ranked: tuple[Ranked, ...]) -> Eval.CaseOutcome:
        if name == self.NO_COVERAGE_CASE:
            uncovered = tuple(item for item in ranked if item.kind == 'no-coverage')
            clear = tuple(item for item in ranked if item.kind == 'clear')
            lexical_matches = [item.id for item in uncovered if item.lexical]
            highest_uncovered = max(
                (item.top_similarity for item in uncovered), default=None
            )
            lowest_clear = min((item.top_similarity for item in clear), default=None)
            passed = (
                bool(uncovered)
                and bool(clear)
                and not lexical_matches
                and highest_uncovered is not None
                and lowest_clear is not None
                and highest_uncovered < lowest_clear
            )
            return self.CaseOutcome(
                passed,
                None if passed else 'retrieval_gate_not_met',
                {
                    'queries_with_lexical_matches': lexical_matches,
                    'highest_uncovered_top_similarity': highest_uncovered,
                    'lowest_clear_top_similarity': lowest_clear,
                },
            )
        metrics = self.per_strategy(ranked)
        hybrid = metrics['hybrid']
        if name == self.RECALL_CASE:
            passed = hybrid['recall_at_10'] >= self.RECALL_AT_10
        else:
            passed = (
                hybrid['mrr'] >= self.MRR and hybrid['mrr'] >= metrics['lexical']['mrr']
            )
        return self.CaseOutcome(
            passed, None if passed else 'retrieval_gate_not_met', metrics
        )

    def report_extras(self) -> dict[str, Any]:
        if self.ranked is None:
            return {}
        return {
            'per_strategy': self.per_strategy(self.ranked),
            'missed_queries': [
                item.id
                for item in self.ranked
                if item.kind != 'no-coverage'
                and not item.relevant.intersection(item.hybrid[:10])
            ],
        }


class RetrievePlanningSkillsE5Eval(RetrievePlanningSkillsEval):
    """The same gates over the TF-IDF + E5 provider, the fallback meaning model.

    Prepares the index through `prepare_planning_indexes` into an in-memory
    repository with the pinned local E5 model, so switching back stays a safe move.
    """

    selector = 'retrieve-planning-skills-e5'
    workflow_id = 'intelligence-retrieve-planning-skills-e5'
    prompt_revision = 'tfidf-e5-small-rrf-v1'
    MODEL_PROFILE: ClassVar[str] = 'local-tfidf-e5-small-rrf'

    def rank_queries(self) -> tuple[RetrievePlanningSkillsEval.Ranked, ...]:
        seed = build_development_seed()
        skills = tuple(
            SkillCatalogEntry(
                id=skill.id, name=skill.name, description=skill.description
            )
            for skill in seed.skills
            if not skill.id.startswith(ROADMAP_SKILL_ID_PREFIX)
        )
        ids_by_name = {skill.name: skill.id for skill in skills}
        catalog = _SeedSkillCatalogProvider(skills)
        embeddings = SentenceTransformersEmbeddingsProvider()
        preprocessor = SpacyPlanningTextPreprocessorProvider(
            self.resources.manifest.negation
        )
        repository = _InMemoryPlanningEmbeddingsRepository()
        version = prepare_indexes(
            embeddings, repository, catalog, self.resources, preprocessor
        )
        provider = TfidfSentenceTransformersPlanningSkillRetrievalProvider(
            skills, embeddings, repository, preprocessor, self.resources
        )
        ranked: list[RetrievePlanningSkillsEval.Ranked] = []
        for item in self.resources.retrieval_evaluation.queries:
            query = PlanningQuery(intent=item.intent, answers=tuple(item.answers))
            vector = embeddings.embed_queries(
                (' '.join((query.intent, *query.answers)),)
            )[0]
            nearest = repository.find_nearest(
                version, vector, tuple(ids_by_name.values()), 1
            )
            ranked.append(
                self.ranked_item(
                    item, ids_by_name, provider.retrieve(query), nearest[0].similarity
                )
            )
        return tuple(ranked)

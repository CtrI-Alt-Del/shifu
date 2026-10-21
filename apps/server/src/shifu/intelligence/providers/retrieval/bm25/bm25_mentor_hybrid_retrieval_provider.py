from typing import cast

from rank_bm25 import BM25Okapi

from shifu.intelligence.ai.data.mentor_resources import MentorResources
from shifu.intelligence.core.interfaces.mentor_embeddings_repository import (
    MentorEmbeddingsRepository,
)
from shifu.intelligence.core.interfaces.mentor_faq_reranker_provider import (
    MentorFaqRerankerProvider,
)
from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
    SpacyMentorTextPreprocessorProvider,
)
from shifu.shared.core.domain.structures.mentor_catalog_entry import MentorCatalogEntry
from shifu.shared.core.domain.errors import ServiceUnavailableError


class Bm25MentorHybridRetrievalProvider:
    _resources: MentorResources
    _repository: MentorEmbeddingsRepository
    _preprocessor: SpacyMentorTextPreprocessorProvider
    _references: tuple[str, ...]
    _bm25: BM25Okapi
    _reranker: MentorFaqRerankerProvider | None

    def __init__(
        self,
        repository: MentorEmbeddingsRepository,
        preprocessor: SpacyMentorTextPreprocessorProvider,
        resources: MentorResources,
        reranker: MentorFaqRerankerProvider | None = None,
    ) -> None:
        self._resources = resources
        self._repository = repository
        self._preprocessor = preprocessor
        self._reranker = reranker
        documents = [
            (answer.id, text)
            for answer in resources.answers
            for text in dict.fromkeys([answer.question, *answer.variations])
        ]
        self._references = tuple(reference for reference, _ in documents)
        self._bm25 = BM25Okapi(
            [list(preprocessor.tokenize(text)) for _, text in documents]
        )

    def retrieve(self, content: str, query: tuple[float, ...]) -> tuple[str, ...]:
        if self._preprocessor.has_unresolved_reference(content):
            return ()
        references = tuple(answer.id for answer in self._resources.answers)
        matches = self._repository.find_nearest(
            'answers', self._resources.version, query, references
        )
        best: dict[str, float] = {}
        for match in matches:
            if match.reference_id in references:
                best[match.reference_id] = max(
                    best.get(match.reference_id, -1), match.similarity
                )
        if not best:
            return ()
        # Retrieve and fuse candidates before deciding whether evidence is sufficient.
        semantic = sorted(best, key=lambda reference: (-best[reference], reference))
        winner = semantic[0]
        runner_up = best[semantic[1]] if len(semantic) > 1 else -1
        manifest = self._resources.manifest
        scores = cast(
            'list[float]',
            self._bm25.get_scores(  # pyright: ignore[reportUnknownMemberType] - rank-bm25 supplies untyped numpy query methods.
                list(self._preprocessor.tokenize(content))
            ).tolist(),
        )
        lexical = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
        lexical_refs = list(
            dict.fromkeys(
                self._references[index] for index in lexical if scores[index] > 0
            )
        )
        fused: dict[str, float] = {}
        for ranking in (semantic, lexical_refs):
            for rank, reference in enumerate(ranking, start=1):
                fused[reference] = fused.get(reference, 0) + 1 / (manifest.rrf_k + rank)
        ranked = sorted(fused, key=lambda reference: (-fused[reference], reference))
        # Preserve the calibrated fast path. RRF is a rank, not confidence.
        if (
            best[winner] >= manifest.faq_cosine_threshold
            and best[winner] - runner_up >= manifest.faq_margin
            and ranked[0] == winner
        ):
            return (winner,)
        return self._rerank(content, ranked, best, semantic)

    def _rerank(
        self,
        content: str,
        ranked: list[str],
        semantic_scores: dict[str, float],
        semantic: list[str],
    ) -> tuple[str, ...]:
        if self._reranker is None:
            return ()
        manifest = self._resources.manifest
        candidates = tuple(
            reference
            for reference in ranked
            if semantic_scores[reference] >= manifest.faq_candidate_cosine_threshold
        )[: manifest.faq_rerank_limit]
        if not candidates:
            return ()
        answers = {answer.id: answer for answer in self._resources.answers}
        documents = tuple(
            '\n'.join(
                (
                    answers[reference].question,
                    *answers[reference].variations,
                    answers[reference].answer,
                )
            )
            for reference in candidates
        )
        try:
            scores = self._reranker.score(content, documents)
        except ServiceUnavailableError:
            return ()
        ordered = sorted(
            zip(candidates, scores, strict=True), key=lambda item: (-item[1], item[0])
        )
        winner, score = ordered[0]
        runner_up = ordered[1][1] if len(ordered) > 1 else 0.0
        if (
            winner not in semantic[:3]
            or score < manifest.faq_rerank_score_threshold
            or score - runner_up < manifest.faq_rerank_margin
        ):
            return ()
        return (winner,)

    def retrieve_curriculum(
        self,
        content: str,
        query: tuple[float, ...],
        projection: tuple[MentorCatalogEntry, ...],
        eligible_references: tuple[str, ...],
        limit: int = 10,
    ) -> tuple[str, ...]:
        eligible = set(eligible_references)
        # Filter every origin before ranking; a blocked origin cannot win a global limit.
        entries = tuple(entry for entry in projection if entry.reference_id in eligible)
        references = tuple(dict.fromkeys(entry.reference_id for entry in entries))
        if not references:
            return ()
        matches = self._repository.find_nearest(
            'curriculum', self._resources.version, query, references
        )
        best: dict[str, float] = {}
        for match in matches:
            if match.reference_id in eligible:
                best[match.reference_id] = max(
                    best.get(match.reference_id, -1), match.similarity
                )
        semantic = sorted(best, key=lambda reference: (-best[reference], reference))
        corpus = [
            list(
                self._preprocessor.tokenize(
                    ' '.join(
                        filter(
                            None,
                            (
                                entry.title,
                                entry.description,
                                *entry.concept_ids,
                            ),
                        )
                    )
                )
            )
            for entry in entries
        ]
        if not any(corpus):
            return tuple(semantic[:limit])
        scores = cast(
            'list[float]',
            BM25Okapi(corpus)
            .get_scores(  # pyright: ignore[reportUnknownMemberType]
                list(self._preprocessor.tokenize(content))
            )
            .tolist(),
        )
        lexical = list(
            dict.fromkeys(
                entries[index].reference_id
                for index in sorted(
                    range(len(scores)), key=lambda index: (-scores[index], index)
                )
                if scores[index] > 0
            )
        )
        fused: dict[str, float] = {}
        for ranking in (semantic, lexical):
            for rank, reference in enumerate(ranking, start=1):
                fused[reference] = fused.get(reference, 0) + 1 / (
                    self._resources.manifest.rrf_k + rank
                )
        return tuple(
            sorted(fused, key=lambda reference: (-fused[reference], reference))[:limit]
        )

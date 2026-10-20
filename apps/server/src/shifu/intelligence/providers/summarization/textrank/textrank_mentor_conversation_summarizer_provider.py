"""Local extractive Mentor conversation summarizer (TextRank, MMR, key phrases)."""

import math
import re
from collections import Counter
from dataclasses import dataclass, replace
from importlib.resources import files
from typing import ClassVar

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

from shifu.intelligence.core.domain.entities import MentorMessage
from shifu.intelligence.core.domain.enums import (
    MentorMessageRole,
    MentorSummaryExcerptKind,
)
from shifu.intelligence.core.domain.structures import (
    MentorConversationSummaryContext,
    MentorConversationSummaryDraft,
    MentorSummaryExcerptSpan,
    fenced_code_ranges,
)
from shifu.intelligence.core.interfaces import MentorEmbeddingsProvider
from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
    SpacyMentorTextPreprocessorProvider,
)

type _Matrix = NDArray[np.float64]

_INLINE_CODE = re.compile(r'`([^`\n]+)`')
_IDENTIFIER = re.compile(
    r'^([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)(?:\(.*\))?$'
)
_LINE = re.compile(r'[^\n]+')
_LEADING_NOISE = re.compile(r'^(?:\d+[.)]\s+)?[\W_]+')


class _CueSet(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid', strict=True, frozen=True
    )
    starts_with: list[str] = Field(min_length=1)
    contains: list[str] = Field(min_length=1)


class _Cues(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid', strict=True, frozen=True
    )
    format_version: int
    cues_version: int = Field(ge=1)
    language: str
    provenance: dict[str, str | bool]
    leading_connectors: list[str] = Field(min_length=1)
    generic_terms: list[str]
    doubt: _CueSet
    guidance: _CueSet


@dataclass(frozen=True, slots=True)
class _Candidate:
    order: int
    message_id: str
    start: int
    end: int
    text: str
    kind: MentorSummaryExcerptKind | None


def _without_fences(content: str) -> str:
    """Blank fenced code with spaces, keeping newlines and every offset."""
    characters = list(content)
    for start, end in fenced_code_ranges(content):
        for index in range(start, min(end, len(characters))):
            if characters[index] != '\n':
                characters[index] = ' '
    return ''.join(characters)


def _mask_inline_code(text: str, fill: str) -> str:
    """Replace inline code with ``fill`` of the same length so offsets are preserved."""
    return _INLINE_CODE.sub(lambda match: fill * len(match.group(0)), text)


class TextrankMentorConversationSummarizerProvider:
    """Summarize a conversation range by ranking its own sentences, locally.

    The result is deterministic for the same input and ``ALGORITHM_VERSION``. Every
    excerpt is a pointer into one source message, never a copy of text.
    """

    ALGORITHM_VERSION: ClassVar[str] = 'textrank-mmr-e5-v1'
    MIN_CONTENT_TOKENS: ClassVar[int] = 4
    E5_COSINE_FLOOR: ClassVar[float] = 0.70
    EDGE_COSINE: ClassVar[float] = 0.30
    DAMPING: ClassVar[float] = 0.85
    MAX_ITERATIONS: ClassVar[int] = 100
    TOLERANCE: ClassVar[float] = 1e-6
    MMR_LAMBDA: ClassVar[float] = 0.70
    SKIP_SIMILARITY: ClassVar[float] = 0.92
    MAX_EXCERPTS_PER_KIND: ClassVar[int] = 5
    MAX_TOPICS: ClassVar[int] = 8
    MAX_CANDIDATES: ClassVar[int] = 512
    MAX_PHRASES: ClassVar[int] = 512
    EXCERPT_MAX_CODE_POINTS: ClassVar[int] = 280
    TOPIC_MAX_CODE_POINTS: ClassVar[int] = 80
    CUES_RESOURCE: ClassVar[str] = 'mentor-summary-cues.json'

    _preprocessor: SpacyMentorTextPreprocessorProvider
    _embeddings: MentorEmbeddingsProvider
    _cues: _Cues
    _version: str
    _connectors: re.Pattern[str]
    _generic: frozenset[str]
    _doubt_start: re.Pattern[str]
    _doubt_contains: re.Pattern[str]
    _guidance_start: re.Pattern[str]
    _guidance_contains: re.Pattern[str]

    def __init__(
        self,
        preprocessor: SpacyMentorTextPreprocessorProvider,
        embeddings: MentorEmbeddingsProvider,
    ) -> None:
        self._preprocessor = preprocessor
        self._embeddings = embeddings
        raw = (
            files('shifu.intelligence.ai.data')
            .joinpath(self.CUES_RESOURCE)
            .read_text(encoding='utf-8')
        )
        self._cues = _Cues.model_validate_json(raw, strict=True)
        self._version = (
            f'{self.ALGORITHM_VERSION}+cues{self._cues.cues_version}'
            f'+cap{self.MAX_CANDIDATES}.{self.MAX_PHRASES}'
        )
        self._connectors = self._leading_pattern(self._cues.leading_connectors)
        self._generic = frozenset(term.casefold() for term in self._cues.generic_terms)
        self._doubt_start = self._start_pattern(self._cues.doubt.starts_with)
        self._doubt_contains = self._contains_pattern(self._cues.doubt.contains)
        self._guidance_start = self._start_pattern(self._cues.guidance.starts_with)
        self._guidance_contains = self._contains_pattern(self._cues.guidance.contains)

    def summarize(
        self,
        messages: tuple[MentorMessage, ...],
        previous: MentorConversationSummaryContext | None,
    ) -> MentorConversationSummaryDraft:
        ordered = tuple(
            sorted(messages, key=lambda message: (message.created_at, message.id))
        )
        fresh = tuple(
            message for message in ordered if not self._is_covered(message, previous)
        )
        candidates = self._capped(self._candidates(fresh))
        carried = self._carried(ordered, previous, start_order=len(candidates))
        sentences = (*candidates, *carried)

        vectors = self._vectors(tuple(sentence.text for sentence in sentences))
        excerpts = self._select_excerpts(sentences, vectors)
        topics = self._select_topics(fresh, previous, vectors)
        return MentorConversationSummaryDraft(
            topics=topics,
            excerpts=excerpts,
            algorithm_version=self._version,
        )

    # --- sentence candidates -------------------------------------------------

    @staticmethod
    def _is_covered(
        message: MentorMessage, previous: MentorConversationSummaryContext | None
    ) -> bool:
        if previous is None:
            return False
        return (message.created_at, message.id) <= (
            previous.boundary.created_at,
            previous.boundary.message_id,
        )

    def _candidates(
        self, messages: tuple[MentorMessage, ...]
    ) -> tuple[_Candidate, ...]:
        candidates: list[_Candidate] = []
        for message in messages:
            visible = _without_fences(message.content)
            for start, end in self._sentence_ranges(visible):
                end = min(end, start + self.EXCERPT_MAX_CODE_POINTS)
                text = message.content[start:end]
                if (
                    not text.strip()
                    or self._preprocessor.content_word_count(text)
                    < self.MIN_CONTENT_TOKENS
                ):
                    continue
                candidates.append(
                    _Candidate(
                        order=len(candidates),
                        message_id=message.id,
                        start=start,
                        end=end,
                        text=text,
                        kind=self._kind(message.role, text),
                    )
                )
        return tuple(candidates)

    def _capped(self, candidates: tuple[_Candidate, ...]) -> tuple[_Candidate, ...]:
        """Bound the similarity matrix: keep cue-bearing sentences first, then the rest.

        Both groups keep their reading order, so the selection is deterministic and a
        range under the cap is returned unchanged.
        """
        if len(candidates) <= self.MAX_CANDIDATES:
            return candidates
        ranked = sorted(
            candidates, key=lambda candidate: (candidate.kind is None, candidate.order)
        )
        kept = sorted(ranked[: self.MAX_CANDIDATES], key=lambda item: item.order)
        return tuple(replace(item, order=index) for index, item in enumerate(kept))

    def _sentence_ranges(self, visible: str) -> tuple[tuple[int, int], ...]:
        """Sentence ranges of prose text, split again at line breaks and trimmed."""
        analysis = _mask_inline_code(visible, 'x')
        ranges: list[tuple[int, int]] = []
        for span in self._preprocessor.segment(analysis):
            for line in _LINE.finditer(visible, span.start, span.end):
                start, end = line.start(), line.end()
                while start < end and visible[start].isspace():
                    start += 1
                while end > start and visible[end - 1].isspace():
                    end -= 1
                if start < end:
                    ranges.append((start, end))
        return tuple(ranges)

    def _carried(
        self,
        messages: tuple[MentorMessage, ...],
        previous: MentorConversationSummaryContext | None,
        *,
        start_order: int,
    ) -> tuple[_Candidate, ...]:
        """Re-resolve the previous excerpts to spans of the messages we were given.

        A previous excerpt carries text but no offsets, so it can only be kept when its
        source message is among ``messages``; otherwise only its topics are folded in.
        """
        if previous is None:
            return ()
        by_id = {message.id: message for message in messages}
        carried: list[_Candidate] = []
        for excerpt in previous.excerpts:
            message = by_id.get(excerpt.message_id)
            if message is None or not excerpt.text.strip():
                continue
            start = message.content.find(excerpt.text)
            end = start + len(excerpt.text)
            if start < 0 or any(
                start < fence_end and end > fence_start
                for fence_start, fence_end in fenced_code_ranges(message.content)
            ):
                continue
            carried.append(
                _Candidate(
                    order=start_order + len(carried),
                    message_id=message.id,
                    start=start,
                    end=end,
                    text=excerpt.text,
                    kind=excerpt.kind,
                )
            )
        return tuple(carried)

    # --- cues ------------------------------------------------------------------

    @staticmethod
    def _alternation(cues: list[str]) -> str:
        return '|'.join(
            re.escape(cue.casefold())
            for cue in sorted(set(cues), key=lambda cue: (-len(cue), cue))
        )

    @classmethod
    def _start_pattern(cls, cues: list[str]) -> re.Pattern[str]:
        return re.compile(rf'^(?:{cls._alternation(cues)})(?!\w)', re.IGNORECASE)

    @classmethod
    def _contains_pattern(cls, cues: list[str]) -> re.Pattern[str]:
        return re.compile(rf'(?<!\w)(?:{cls._alternation(cues)})(?!\w)', re.IGNORECASE)

    @classmethod
    def _leading_pattern(cls, cues: list[str]) -> re.Pattern[str]:
        return re.compile(
            rf'^(?:{cls._alternation(cues)})(?!\w)[\s,;:!.\-\u2013\u2014]*',
            re.IGNORECASE,
        )

    def _kind(
        self, role: MentorMessageRole, text: str
    ) -> MentorSummaryExcerptKind | None:
        forms = self._cue_forms(text)
        if role is MentorMessageRole.LEARNER:
            if (
                text.rstrip().endswith('?')
                or any(self._doubt_start.search(form) for form in forms)
                or self._doubt_contains.search(forms[0])
            ):
                return MentorSummaryExcerptKind.DOUBT
            return None
        if any(self._guidance_start.search(form) for form in forms) or (
            self._guidance_contains.search(forms[0])
        ):
            return MentorSummaryExcerptKind.GUIDANCE
        return None

    def _cue_forms(self, text: str) -> tuple[str, ...]:
        """The sentence without leading marks, then without leading connectors."""
        form = _LEADING_NOISE.sub('', text.casefold())
        forms = [form]
        while match := self._connectors.match(form):
            form = _LEADING_NOISE.sub('', form[match.end() :])
            forms.append(form)
        return tuple(forms)

    # --- ranking ---------------------------------------------------------------

    def _select_excerpts(
        self, sentences: tuple[_Candidate, ...], vectors: _Matrix
    ) -> tuple[MentorSummaryExcerptSpan, ...]:
        if not sentences:
            return ()
        similarity = self._similarity(vectors)
        relevance = self._pagerank(similarity)
        peak = float(relevance.max())
        relevance = relevance / peak if peak > 0 else relevance

        chosen: list[int] = []
        for kind in MentorSummaryExcerptKind:
            eligible = [
                index
                for index, sentence in enumerate(sentences)
                if sentence.kind is kind
            ]
            chosen.extend(
                self._mmr(relevance, similarity, eligible, self.MAX_EXCERPTS_PER_KIND)
            )
        spans: list[MentorSummaryExcerptSpan] = []
        for index in sorted(chosen, key=lambda item: sentences[item].order):
            sentence = sentences[index]
            if sentence.kind is None:
                continue
            spans.append(
                MentorSummaryExcerptSpan(
                    message_id=sentence.message_id,
                    start=sentence.start,
                    end=sentence.end,
                    kind=sentence.kind,
                )
            )
        return tuple(spans)

    def _vectors(self, texts: tuple[str, ...]) -> _Matrix:
        if not texts:
            return np.zeros((0, 0), dtype=np.float64)
        matrix = np.asarray(self._embeddings.embed_passages(texts), dtype=np.float64)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return matrix / np.where(norms > 0, norms, 1.0)

    def _similarity(self, vectors: _Matrix) -> _Matrix:
        """Cosine similarity rescaled from the E5 floor to [0, 1].

        E5 documents cosines between unrelated texts around 0.70, so the fixed
        thresholds below are applied to ``(cosine - floor) / (1 - floor)``.
        """
        cosine: _Matrix = vectors @ vectors.T
        scaled = (cosine - self.E5_COSINE_FLOOR) / (1.0 - self.E5_COSINE_FLOOR)
        return np.clip(scaled, 0.0, 1.0)

    def _pagerank(self, similarity: _Matrix) -> _Matrix:
        size = similarity.shape[0]
        weights = np.where(similarity >= self.EDGE_COSINE, similarity, 0.0)
        np.fill_diagonal(weights, 0.0)
        totals = weights.sum(axis=0)
        transition = weights / np.where(totals > 0, totals, 1.0)
        dangling = totals == 0
        rank: _Matrix = np.full(size, 1.0 / size)
        for _ in range(self.MAX_ITERATIONS):
            updated = (1.0 - self.DAMPING) / size + self.DAMPING * (
                transition @ rank + rank[dangling].sum() / size
            )
            converged = float(np.abs(updated - rank).sum()) < self.TOLERANCE
            rank = updated
            if converged:
                break
        return rank

    def _mmr(
        self,
        relevance: _Matrix,
        similarity: _Matrix,
        eligible: list[int],
        limit: int,
    ) -> list[int]:
        """Greedy maximal marginal relevance.

        Relevance is min-max scaled across the eligible items, the redundancy penalty is
        the raw cosine to the closest selected item, and an item at or above the skip
        similarity of a selected one is dropped.
        """
        if not eligible:
            return []
        scaled = self._scale(relevance[eligible])
        block = similarity[np.ix_(eligible, eligible)]

        selected: list[int] = []
        remaining = list(range(len(eligible)))
        while remaining and len(selected) < limit:
            best: int | None = None
            best_score = -math.inf
            for position in tuple(remaining):
                redundancy = max(
                    (float(block[position, other]) for other in selected),
                    default=0.0,
                )
                redundancy = max(redundancy, 0.0)
                if redundancy >= self.SKIP_SIMILARITY:
                    remaining.remove(position)
                    continue
                score = (
                    self.MMR_LAMBDA * float(scaled[position])
                    - (1.0 - self.MMR_LAMBDA) * redundancy
                )
                if score > best_score:
                    best, best_score = position, score
            if best is None:
                break
            selected.append(best)
            remaining.remove(best)
        return [eligible[position] for position in selected]

    @staticmethod
    def _scale(values: _Matrix) -> _Matrix:
        low, high = float(values.min()), float(values.max())
        if high <= low:
            return np.ones_like(values)
        return (values - low) / (high - low)

    # --- topics ----------------------------------------------------------------

    def _select_topics(
        self,
        fresh: tuple[MentorMessage, ...],
        previous: MentorConversationSummaryContext | None,
        sentence_vectors: _Matrix,
    ) -> tuple[str, ...]:
        counts: Counter[tuple[str, ...]] = Counter()
        surfaces: dict[tuple[str, ...], str] = {}
        if previous is not None:
            for topic in previous.topics:
                self._count(topic, counts, surfaces)
        for message in fresh:
            for phrase in self._phrases(message.content):
                self._count(phrase, counts, surfaces)
        if not surfaces:
            return ()

        keys = tuple(surfaces)
        if len(keys) > self.MAX_PHRASES:
            # Bound the phrase similarity matrix: most frequent first, then first seen.
            frequent = set(
                sorted(keys, key=lambda key: -counts[key])[: self.MAX_PHRASES]
            )
            keys = tuple(key for key in keys if key in frequent)
        phrase_vectors = self._vectors(tuple(surfaces[key] for key in keys))
        if len(sentence_vectors):
            reference = sentence_vectors.mean(axis=0)
        else:
            reference = phrase_vectors.mean(axis=0)
        norm = float(np.linalg.norm(reference))
        reference = reference / norm if norm > 0 else reference
        weights = np.asarray(
            [1.0 + math.log(counts[key]) for key in keys], dtype=np.float64
        )
        score: _Matrix = (phrase_vectors @ reference) * weights
        peak = float(score.max())
        relevance = score / peak if peak > 0 else score
        chosen = self._mmr(
            relevance,
            self._similarity(phrase_vectors),
            list(range(len(keys))),
            self.MAX_TOPICS,
        )
        return tuple(surfaces[keys[index]] for index in chosen)

    def _count(
        self,
        phrase: str,
        counts: Counter[tuple[str, ...]],
        surfaces: dict[tuple[str, ...], str],
    ) -> None:
        surface = ' '.join(phrase.split())
        if not surface or len(surface) > self.TOPIC_MAX_CODE_POINTS:
            return
        if not any(character.isalpha() for character in surface):
            return
        key = tuple(self._preprocessor.tokenize(surface)) or (surface.casefold(),)
        if all(token in self._generic for token in key):
            return
        counts[key] += 1
        surfaces.setdefault(key, surface)

    def _phrases(self, content: str) -> tuple[str, ...]:
        visible = _without_fences(content)
        identifiers = tuple(
            match.group(1)
            for code in _INLINE_CODE.finditer(visible)
            if (match := _IDENTIFIER.match(code.group(1).strip()))
        )
        prose = _mask_inline_code(visible, ' ')
        return (*self._preprocessor.noun_phrases(prose), *identifiers)

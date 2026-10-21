from threading import RLock
from typing import ClassVar

import spacy
from spacy.language import Language
from spacy.tokens import Doc

from shifu.intelligence.core.domain.structures.mentor_text_span import MentorTextSpan


class SpacyMentorTextPreprocessorProvider:
    _NEGATION: ClassVar[frozenset[str]] = frozenset(
        {'não', 'nao', 'nunca', 'nem', 'sem', 'jamais'}
    )
    _REQUEST_VERBS: ClassVar[frozenset[str]] = frozenset(
        {'querer', 'pedir', 'perguntar', 'solicitar', 'explicar', 'responder'}
    )
    _PHRASE_EDGE_POS: ClassVar[frozenset[str]] = frozenset(
        {'DET', 'ADP', 'PRON', 'CCONJ', 'SCONJ', 'PUNCT', 'SPACE', 'AUX', 'PART', 'ADV'}
    )
    _PHRASE_MAX_TOKENS: ClassVar[int] = 3
    _CONTENT_POS: ClassVar[frozenset[str]] = frozenset(
        {'NOUN', 'PROPN', 'VERB', 'ADJ', 'NUM'}
    )
    _pipeline: Language | None
    _lock: RLock

    def __init__(self, *, lazy: bool = False) -> None:
        # The shared composition loads the pipeline on first use so building the
        # registry never reads model files; direct construction stays eager.
        self._lock = RLock()
        self._pipeline = None if lazy else self._load()

    @staticmethod
    def _load() -> Language:
        return spacy.load('pt_core_news_sm', exclude=['ner'])

    def _parse(self, text: str) -> Doc:
        # One pipeline is shared by routing and summarization; parse serially.
        with self._lock:
            if self._pipeline is None:
                self._pipeline = self._load()
            return self._pipeline(text)

    def is_negated_request(self, text: str) -> bool:
        return any(
            token.text.casefold() in {'não', 'nao', 'nunca', 'jamais'}
            and token.head.lemma_.casefold() in self._REQUEST_VERBS
            for token in self._parse(text)
        )

    def has_unresolved_reference(self, text: str) -> bool:
        return any(
            token.lemma_.casefold() in {'isso', 'aquilo'} for token in self._parse(text)
        )

    def tokenize(self, text: str) -> tuple[str, ...]:
        return tuple(
            (token.lemma_ or token.text).casefold()
            for token in self._parse(text)
            if not token.is_space
            and not token.is_punct
            and (not token.is_stop or token.text.casefold() in self._NEGATION)
        )

    def content_word_count(self, text: str) -> int:
        """Count nouns, proper nouns, verbs, adjectives and numbers in ``text``."""
        return sum(1 for token in self._parse(text) if token.pos_ in self._CONTENT_POS)

    def segment(self, text: str) -> tuple[MentorTextSpan, ...]:
        """Return trimmed, non-empty sentence spans as code-point offsets of ``text``."""
        spans: list[MentorTextSpan] = []
        for sentence in self._parse(text).sents:
            start, end = sentence.start_char, sentence.end_char
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end - 1].isspace():
                end -= 1
            if start < end:
                spans.append(MentorTextSpan(start=start, end=end))
        return tuple(spans)

    def noun_phrases(self, text: str) -> tuple[str, ...]:
        """Return short noun phrases of ``text`` without articles or prepositions."""
        phrases: list[str] = []
        for chunk in self._parse(text).noun_chunks:
            tokens = list(chunk)
            while tokens and tokens[0].pos_ in self._PHRASE_EDGE_POS:
                tokens.pop(0)
            while tokens and tokens[-1].pos_ in self._PHRASE_EDGE_POS:
                tokens.pop()
            if not tokens:
                continue
            tokens = tokens[-self._PHRASE_MAX_TOKENS :]
            if not any(token.pos_ in {'NOUN', 'PROPN'} for token in tokens):
                continue
            if (
                len(tokens) == 1
                and tokens[0].pos_ == 'PROPN'
                and tokens[0].is_sent_start
            ):
                # Sentence-initial capitalization makes this tag unreliable (greetings, imperatives).
                continue
            surface = ' '.join(token.text for token in tokens)
            phrases.append(
                surface
                if any(token.pos_ == 'PROPN' for token in tokens)
                else surface.casefold()
            )
        return tuple(phrases)

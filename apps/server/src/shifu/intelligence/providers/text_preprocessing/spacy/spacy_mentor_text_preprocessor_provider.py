import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from threading import RLock
from typing import ClassVar

import spacy
from spacy.language import Language
from spacy.tokens import Doc, Span, Token

from shifu.intelligence.core.domain.structures.learner_memory_concept import (
    LearnerMemoryConcept,
)
from shifu.intelligence.core.domain.structures.mentor_text_span import MentorTextSpan


def _normalize(value: str) -> str:
    """Casefold and strip accents so typed variants compare equal."""
    decomposed = unicodedata.normalize('NFKD', value.casefold())
    return ''.join(char for char in decomposed if not unicodedata.combining(char))


@dataclass(frozen=True, slots=True)
class LearnerSentence:
    """One sentence of a learner message, analyzed in the message's single parse."""

    text: str
    is_eligible: bool
    tokens: tuple[str, ...]
    concepts: tuple[LearnerMemoryConcept, ...]


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
    _LEARNER_NEGATION: ClassVar[frozenset[str]] = frozenset(
        {'nao', 'nunca', 'nem', 'sem', 'jamais'}
    )
    # Closed lexicon of first-person-singular forms. The small model often tags
    # these as proper nouns or gerunds, so token.morph alone misses them.
    _FIRST_PERSON_FORMS: ClassVar[frozenset[str]] = frozenset(
        _normalize(form)
        for form in (
            'prefiro',
            'gosto',
            'adoro',
            'amo',
            'quero',
            'pretendo',
            'planejo',
            'espero',
            'desejo',
            'sonho',
            'preciso',
            'tenho',
            'sei',
            'conheço',
            'domino',
            'entendo',
            'compreendo',
            'aprendo',
            'uso',
            'utilizo',
            'programo',
            'faço',
            'consigo',
            'acho',
            'penso',
            'fico',
            'estou',
            'sou',
            'vou',
            'travo',
            'confundo',
            'esqueço',
            'perco',
            'sinto',
            'costumo',
            'erro',
            'tive',
            'fiz',
            'aprendi',
            'estudei',
            'entendi',
            'terminei',
            'concluí',
            'usei',
            'programei',
            'consegui',
            'errei',
            'travei',
            'esqueci',
            'confundi',
            'perdi',
            'senti',
            'decidi',
            'comecei',
            'estudo',
            'trabalho',
            'evito',
        )
    )
    _AMBIGUOUS_FORMS: ClassVar[frozenset[str]] = frozenset(
        {'gosto', 'uso', 'estudo', 'trabalho', 'erro', 'amo', 'perco'}
    )
    _INTERROGATIVES: ClassVar[frozenset[str]] = frozenset(
        {
            'como',
            'qual',
            'quais',
            'quem',
            'quando',
            'onde',
            'aonde',
            'quanto',
            'quanta',
            'quantos',
            'quantas',
        }
    )
    _SUBJECT_POS: ClassVar[frozenset[str]] = frozenset({'NOUN', 'PROPN', 'ADJ', 'VERB'})
    _CONCEPT_MAX_TOKENS: ClassVar[int] = 3
    _CONCEPT_MAX_COUNT: ClassVar[int] = 3
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

    def learner_sentences(
        self, text: str, cue_words: frozenset[str]
    ) -> tuple[LearnerSentence, ...]:
        """Analyze every non-empty sentence of ``text`` in a single parse.

        ``cue_words`` are accent-stripped and casefolded. Tokens and concepts are
        computed only for eligible sentences (the learner is the subject and the
        sentence is not a question).
        """
        sentences: list[LearnerSentence] = []
        for sentence in self._parse(text).sents:
            trimmed = sentence.text.strip()
            if not any(char.isalnum() for char in trimmed):
                continue
            eligible = self._is_eligible(sentence, trimmed)
            sentences.append(
                LearnerSentence(
                    text=trimmed,
                    is_eligible=eligible,
                    tokens=self._classification_tokens(sentence) if eligible else (),
                    concepts=(self._concepts(sentence, cue_words) if eligible else ()),
                )
            )
        return tuple(sentences)

    def classification_tokens(self, text: str) -> tuple[str, ...]:
        """Lemmatized, accent-stripped tokens that keep "eu" and negations."""
        return self._classification_tokens(self._parse(text))

    def subject_terms(self, text: str, cue_words: frozenset[str]) -> tuple[str, ...]:
        """Lemmatized, casefolded, accent-stripped content terms without cue words."""
        terms: list[str] = []
        for token in self._parse(text):
            if token.pos_ not in self._SUBJECT_POS or token.is_stop:
                continue
            surface = _normalize(token.text)
            lemma = _normalize(token.lemma_ or token.text)
            if surface in cue_words or lemma in cue_words or not lemma.strip():
                continue
            terms.append(lemma)
        return tuple(terms)

    def learner_concepts(
        self, text: str, cue_words: frozenset[str]
    ) -> tuple[LearnerMemoryConcept, ...]:
        """Up to three noun-phrase concepts of ``text`` (edit path, no classifier)."""
        return self._concepts(self._parse(text), cue_words)

    def _is_eligible(self, sentence: Span, trimmed: str) -> bool:
        if self._is_question(sentence, trimmed):
            return False
        return any(self._is_learner_subject(token) for token in sentence)

    def _is_question(self, sentence: Span, trimmed: str) -> bool:
        if trimmed.rstrip(' "\')!.\u201d\u2019').endswith('?'):
            return True
        words = [_normalize(token.text) for token in sentence if token.is_alpha]
        if not words:
            return False
        if words[0] in self._INTERROGATIVES:
            return True
        return words[:2] in (['o', 'que'], ['por', 'que'])

    def _is_learner_subject(self, token: Token) -> bool:
        if token.lower_ == 'eu':
            return True
        return self._is_first_person_singular(token)

    def _is_first_person_singular(self, token: Token) -> bool:
        if token.pos_ in {'VERB', 'AUX'}:
            morph = token.morph.to_dict()
            if morph.get('Person') == '1' and morph.get('Number') == 'Sing':
                return True
        form = _normalize(token.text)
        if form not in self._FIRST_PERSON_FORMS:
            return False
        if token.pos_ in {'VERB', 'AUX', 'PROPN'} or form not in self._AMBIGUOUS_FORMS:
            return True
        # A noun reading ("o gosto", "no trabalho") follows a determiner or preposition.
        return token.i == 0 or token.nbor(-1).pos_ not in {'DET', 'ADP', 'NUM', 'ADJ'}

    def _classification_tokens(self, tokens: Iterable[Token]) -> tuple[str, ...]:
        result: list[str] = []
        for token in tokens:
            if token.is_space or token.is_punct:
                continue
            if self._is_first_person_singular(token):
                value = _normalize(token.text)
            elif token.lower_ == 'eu':
                value = 'eu'
            else:
                if token.is_stop and (
                    _normalize(token.text) not in self._LEARNER_NEGATION
                ):
                    continue
                value = _normalize(token.lemma_ or token.text)
            value = value.strip()
            if value:
                result.append(value)
        return tuple(result)

    def _concepts(
        self, container: Doc | Span, cue_words: frozenset[str]
    ) -> tuple[LearnerMemoryConcept, ...]:
        concepts: dict[str, LearnerMemoryConcept] = {}
        for chunk in container.noun_chunks:
            tokens = [
                token
                for token in chunk
                if token.pos_ != 'DET'
                and _normalize(token.text) not in cue_words
                and _normalize(token.lemma_ or token.text) not in cue_words
            ]
            while tokens and tokens[0].pos_ in self._PHRASE_EDGE_POS:
                tokens.pop(0)
            while tokens and tokens[-1].pos_ in self._PHRASE_EDGE_POS:
                tokens.pop()
            tokens = tokens[: self._CONCEPT_MAX_TOKENS]
            if not any(token.pos_ in {'NOUN', 'PROPN'} for token in tokens):
                continue
            key = ' '.join(_normalize(token.lemma_ or token.text) for token in tokens)
            key = re.sub(r'\s+', ' ', key).strip()
            surface = ' '.join(token.text for token in tokens).strip()
            if not key or not surface or key in concepts:
                continue
            if len(key) > LearnerMemoryConcept.MAX_CODE_POINTS or (
                len(surface) > LearnerMemoryConcept.MAX_CODE_POINTS
            ):
                continue
            label = surface[:1].upper() + surface[1:]
            concepts[key] = LearnerMemoryConcept(key=key, label=label)
            if len(concepts) == self._CONCEPT_MAX_COUNT:
                break
        return tuple(concepts.values())

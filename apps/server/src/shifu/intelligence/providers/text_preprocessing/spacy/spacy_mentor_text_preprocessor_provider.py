from typing import ClassVar

import spacy
from spacy.language import Language


class SpacyMentorTextPreprocessorProvider:
    _NEGATION: ClassVar[frozenset[str]] = frozenset(
        {'não', 'nao', 'nunca', 'nem', 'sem', 'jamais'}
    )
    _pipeline: Language
    _REQUEST_VERBS: ClassVar[frozenset[str]] = frozenset(
        {'querer', 'pedir', 'perguntar', 'solicitar', 'explicar', 'responder'}
    )

    def __init__(self) -> None:
        self._pipeline = spacy.load('pt_core_news_sm', exclude=['ner'])

    def is_negated_request(self, text: str) -> bool:
        return any(
            token.text.casefold() in {'não', 'nao', 'nunca', 'jamais'}
            and token.head.lemma_.casefold() in self._REQUEST_VERBS
            for token in self._pipeline(text)
        )

    def has_unresolved_reference(self, text: str) -> bool:
        return any(
            token.lemma_.casefold() in {'isso', 'aquilo'}
            for token in self._pipeline(text)
        )

    def tokenize(self, text: str) -> tuple[str, ...]:
        return tuple(
            (token.lemma_ or token.text).casefold()
            for token in self._pipeline(text)
            if not token.is_space
            and not token.is_punct
            and (not token.is_stop or token.text.casefold() in self._NEGATION)
        )

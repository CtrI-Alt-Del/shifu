import unicodedata
from collections.abc import Iterable

import spacy
from spacy.language import Language


class SpacyPlanningTextPreprocessorProvider:
    _pipeline: Language
    _negation: frozenset[str]

    def __init__(self, negation: Iterable[str]) -> None:
        # Negation tokens come from the versioned manifest, never from a local guess.
        self._negation = frozenset(token.casefold() for token in negation)
        if not self._negation:
            raise ValueError('Planner negation tokens cannot be empty')
        self._pipeline = spacy.load('pt_core_news_sm', exclude=['ner'])

    def normalize(self, text: str) -> str:
        return ' '.join(unicodedata.normalize('NFC', text).split())

    def lexical_tokens(self, text: str) -> tuple[str, ...]:
        return tuple(
            (token.lemma_ or token.text).casefold()
            for token in self._pipeline(self.normalize(text))
            if not token.is_space
            and not token.is_punct
            and (not token.is_stop or token.text.casefold() in self._negation)
        )

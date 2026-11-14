from typing import Protocol


class PlanningTextPreprocessorProvider(Protocol):
    def normalize(self, text: str) -> str:
        """Return the original text normalized for the semantic representation."""
        ...

    def lexical_tokens(self, text: str) -> tuple[str, ...]:
        """Return lemmatized pt-BR tokens without stop words, keeping negations."""
        ...

    def word_tokens(self, text: str) -> tuple[str, ...]:
        """Return the words as written, casefolded, without stop words."""
        ...

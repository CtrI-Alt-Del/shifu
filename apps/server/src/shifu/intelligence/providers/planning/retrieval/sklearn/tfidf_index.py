import math
from collections import Counter
from typing import Protocol, cast

import numpy as np
from numpy.typing import NDArray
from sklearn.feature_extraction.text import TfidfVectorizer


def _identity(tokens: list[str]) -> list[str]:
    return tokens


class _SparseMatrix(Protocol):
    """The scipy sparse surface this adapter relies on."""

    @property
    def T(self) -> '_SparseMatrix': ...  # noqa: N802 - scipy attribute name.
    def __matmul__(self, other: '_SparseMatrix') -> '_SparseMatrix': ...
    def toarray(self) -> NDArray[np.float64]: ...


class TfidfIndex:
    """Contain the untyped scikit-learn surface behind a typed cosine scorer."""

    _vectorizer: TfidfVectorizer
    _matrix: _SparseMatrix
    _idf: dict[str, float]
    _unseen_idf: float

    def __init__(self, documents: list[list[str]]) -> None:
        # scikit-learn accepts a callable analyzer; Pyright infers the string default.
        self._vectorizer = TfidfVectorizer(
            analyzer=_identity,  # pyright: ignore[reportArgumentType]
            norm='l2',
        )
        self._matrix = cast('_SparseMatrix', self._vectorizer.fit_transform(documents))  # pyright: ignore[reportUnknownMemberType] - scikit-learn ships no type information.
        vocabulary = cast('dict[str, int]', self._vectorizer.vocabulary_)
        idf = cast('NDArray[np.float64]', self._vectorizer.idf_)
        self._idf = {term: float(idf[column]) for term, column in vocabulary.items()}
        # Smoothed idf, ln((1 + n) / (1 + df)) + 1, for a term no document holds.
        self._unseen_idf = math.log(1 + len(documents)) + 1

    def scores(self, tokens: list[str]) -> list[float]:
        if not tokens:
            return []
        query = cast(
            '_SparseMatrix',
            self._vectorizer.transform([tokens]),  # pyright: ignore[reportUnknownMemberType] - scikit-learn ships no type information.
        )
        # Both sides are L2-normalized, so the dot product is the cosine similarity.
        return [float(value) for value in (self._matrix @ query.T).toarray().ravel()]

    def weights(self, tokens: list[str]) -> dict[str, float]:
        """TF-IDF weight of each token: its count times its idf in the catalog.

        A token the catalog never used is as rare as possible, so it takes the
        highest idf instead of being dropped.
        """
        return {
            token: count * self._idf.get(token, self._unseen_idf)
            for token, count in Counter(tokens).items()
        }

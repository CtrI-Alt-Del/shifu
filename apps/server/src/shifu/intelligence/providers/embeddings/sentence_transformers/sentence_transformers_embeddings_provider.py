from threading import Lock
from typing import ClassVar, cast

import numpy as np
from sentence_transformers import SentenceTransformer

from shifu.shared.core.domain.errors import ServiceUnavailableError


class SentenceTransformersEmbeddingsProvider:
    MODEL: ClassVar[str] = 'intfloat/multilingual-e5-small'
    REVISION: ClassVar[str] = '614241f622f53c4eeff9890bdc4f31cfecc418b3'
    DIMENSION: ClassVar[int] = 384
    _model: SentenceTransformer
    _lock: Lock

    def __init__(
        self, *, cache_folder: str | None = None, local_files_only: bool = True
    ) -> None:
        # Preparation may explicitly resolve weights; requests only use an existing cache.
        self._model = SentenceTransformer(
            self.MODEL,
            revision=self.REVISION,
            cache_folder=cache_folder,
            local_files_only=local_files_only,
            trust_remote_code=False,
        )
        if self._model.get_embedding_dimension() != self.DIMENSION:
            raise ServiceUnavailableError('Índice do Mentor incompatível.')
        # The router (event-loop thread) and the summarizer (worker thread) share this
        # instance; neither the tokenizer nor the model is safe for concurrent calls.
        self._lock = Lock()

    def embed_queries(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return self._encode(texts, 'query: ')

    def embed_passages(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return self._encode(texts, 'passage: ')

    def _encode(
        self, texts: tuple[str, ...], prefix: str
    ) -> tuple[tuple[float, ...], ...]:
        if not texts:
            return ()
        # E5 has a finite token window. Never silently discard the query tail.
        prefixed = [prefix + text for text in texts]
        with self._lock:
            tokens = self._model.tokenizer(prefixed, truncation=False)
            lengths = cast('list[list[int]]', tokens['input_ids'])
            max_length = self._model.max_seq_length
            if max_length is None or any(len(row) > max_length for row in lengths):
                raise ServiceUnavailableError(
                    'Texto excede a capacidade do índice do Mentor.'
                )
            encoded = self._model.encode(  # pyright: ignore[reportUnknownMemberType] - SDK overload exposes unsupported multimodal types.
                prefixed,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        array = np.asarray(encoded, dtype=np.float32)
        if array.shape != (len(texts), self.DIMENSION) or not np.isfinite(array).all():
            raise ServiceUnavailableError('Índice do Mentor incompatível.')
        return tuple(tuple(float(value) for value in row) for row in array)

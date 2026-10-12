from threading import Lock
from typing import TYPE_CHECKING, ClassVar, Protocol, cast

import numpy as np

from shifu.shared.core.domain.errors import ServiceUnavailableError

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder


class _PairTokenizer(Protocol):
    def __call__(
        self, text: list[str], text_pair: list[str], *, truncation: bool
    ) -> dict[str, list[list[int]]]: ...


class SentenceTransformersMentorFaqRerankerProvider:
    MODEL: ClassVar[str] = 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'
    REVISION: ClassVar[str] = '1427fd652930e4ba29e8149678df786c240d8825'
    _UNAVAILABLE: ClassVar[str] = (
        'A seleção local de respostas do Mentor está indisponível.'
    )
    _MAX_DOCUMENTS: ClassVar[int] = 6

    def __init__(
        self, *, cache_folder: str | None = None, local_files_only: bool = True
    ) -> None:
        self._model: CrossEncoder | None = None
        self._lock: Lock = Lock()
        self._cache_folder: str | None = cache_folder
        self._local_files_only: bool = local_files_only

    def prepare(self) -> None:
        """Explicit preparation may download; ordinary construction never loads assets."""
        with self._lock:
            self._load()

    def _load(self) -> 'CrossEncoder':
        if self._model is not None:
            return self._model
        from sentence_transformers import CrossEncoder
        from torch.nn import Identity

        try:
            model = CrossEncoder(
                self.MODEL,
                revision=self.REVISION,
                cache_folder=self._cache_folder,
                local_files_only=self._local_files_only,
                trust_remote_code=False,
                activation_fn=Identity(),
            )
        except (OSError, ValueError, RuntimeError):
            raise ServiceUnavailableError(self._UNAVAILABLE) from None
        self._model = model
        return model

    def score(self, content: str, documents: tuple[str, ...]) -> tuple[float, ...]:
        if not documents:
            return ()
        if (
            not content.strip()
            or len(documents) > self._MAX_DOCUMENTS
            or any(not document.strip() for document in documents)
        ):
            raise ServiceUnavailableError(self._UNAVAILABLE)
        with self._lock:
            model = self._load()
            try:
                tokenizer = cast('_PairTokenizer', model.tokenizer)
                tokens = tokenizer(
                    [content] * len(documents), list(documents), truncation=False
                )
                lengths = tokens['input_ids']
                max_length = model.max_seq_length
                if (
                    len(lengths) != len(documents)
                    or max_length is None
                    or max_length <= 0
                    or any(len(row) > max_length for row in lengths)
                ):
                    raise ServiceUnavailableError(
                        'Texto excede a capacidade da seleção de respostas do Mentor.'
                    )
                scores = model.predict(  # pyright: ignore[reportUnknownMemberType] - SDK prediction overload includes unparameterized numpy arrays.
                    [(content, document) for document in documents],
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                array = np.asarray(scores, dtype=np.float64)
            except (OSError, ValueError, RuntimeError, TypeError, KeyError):
                raise ServiceUnavailableError(self._UNAVAILABLE) from None
            if array.shape != (len(documents),) or not np.isfinite(array).all():
                raise ServiceUnavailableError(self._UNAVAILABLE)
            return tuple(float(value) for value in array)

"""NILC Word2Vec skip-gram vectors for Portuguese, read straight from disk."""

import json
import struct
from pathlib import Path
from typing import ClassVar

import numpy as np
from huggingface_hub import hf_hub_download  # pyright: ignore[reportUnknownVariableType] - the SDK leaves part of the signature untyped.
from numpy.typing import NDArray

from shifu.shared.core.domain.errors import ServiceUnavailableError

_UNAVAILABLE = 'Os vetores de palavras do Planejador não estão disponíveis.'


class NilcWord2VecWordVectorsProvider:
    """Word2Vec trained by NILC-USP on ~1.39B Portuguese tokens (CC BY 4.0).

    The vocabulary file is ordered by frequency; only the most frequent words are
    kept so the lookup table stays small. The matrix is memory-mapped, so the
    operating system only reads the rows of the words actually looked up.
    """

    REPOSITORY: ClassVar[str] = 'nilc-nlp/word2vec-skip-gram-100d'
    REVISION: ClassVar[str] = 'f41e235fbcc31deefdd1da9a2b82a0008c6c861e'
    DIMENSION: ClassVar[int] = 100
    VOCABULARY_LIMIT: ClassVar[int] = 300_000

    _rows: dict[str, int]
    _matrix: NDArray[np.float32]

    def __init__(
        self, *, cache_folder: str | None = None, local_files_only: bool = True
    ) -> None:
        # Preparation may download the files; requests only use the local cache.
        try:
            vocabulary = self._download('vocab.txt', cache_folder, local_files_only)
            embeddings = self._download(
                'embeddings.safetensors', cache_folder, local_files_only
            )
            self._matrix = self._map_matrix(embeddings)
            self._rows = self._read_vocabulary(vocabulary, len(self._matrix))
        except (OSError, ValueError) as error:
            raise ServiceUnavailableError(_UNAVAILABLE) from error

    @property
    def dimension(self) -> int:
        return self.DIMENSION

    def vectors_of(self, words: tuple[str, ...]) -> dict[str, tuple[float, ...]]:
        return {
            word: tuple(float(value) for value in self._matrix[self._rows[word]])
            for word in dict.fromkeys(words)
            if word in self._rows
        }

    def _download(
        self, filename: str, cache_folder: str | None, local_files_only: bool
    ) -> Path:
        return Path(
            hf_hub_download(
                self.REPOSITORY,
                filename,
                revision=self.REVISION,
                cache_dir=cache_folder,
                local_files_only=local_files_only,
            )
        )

    def _map_matrix(self, path: Path) -> NDArray[np.float32]:
        # safetensors: an 8-byte little-endian header size, a JSON header, the data.
        with path.open('rb') as file:
            (header_size,) = struct.unpack('<Q', file.read(8))
            header = json.loads(file.read(header_size))
        tensor = header['embeddings']
        rows, columns = tensor['shape']
        start, _ = tensor['data_offsets']
        if tensor['dtype'] != 'F32' or columns != self.DIMENSION:
            raise ValueError('Unexpected Word2Vec matrix layout')
        matrix = np.memmap(
            path,
            dtype='<f4',
            mode='r',
            offset=8 + header_size + start,
            shape=(rows, columns),
        )
        return matrix[: min(rows, self.VOCABULARY_LIMIT)]

    def _read_vocabulary(self, path: Path, limit: int) -> dict[str, int]:
        rows: dict[str, int] = {}
        with path.open(encoding='utf-8') as file:
            for row, line in enumerate(file):
                if row >= limit:
                    break
                rows.setdefault(line.rstrip('\n'), row)
        if len(rows) < min(limit, self.VOCABULARY_LIMIT) // 2:
            raise ValueError('The Word2Vec vocabulary does not match its matrix')
        return rows

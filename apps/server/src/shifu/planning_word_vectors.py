"""Application entry point for explicit, offline Planner word vector download."""

from shifu.intelligence.providers.planning.word_vectors.huggingface.nilc_word2vec_word_vectors_provider import (
    NilcWord2VecWordVectorsProvider,
)


def main() -> None:
    NilcWord2VecWordVectorsProvider(local_files_only=False)
    print(
        'Planner word vectors ready: '
        f'{NilcWord2VecWordVectorsProvider.REPOSITORY}'
        f'@{NilcWord2VecWordVectorsProvider.REVISION}'
    )


if __name__ == '__main__':
    main()

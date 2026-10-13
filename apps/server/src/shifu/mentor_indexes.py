"""Application entry point for explicit, offline Mentor index preparation."""

from shifu.composition.mentor_dependencies import build_mentor_index_dependencies
from shifu.intelligence.ai.data.mentor_resources import MentorResources
from shifu.intelligence.prepare_mentor_indexes import prepare_indexes
from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
    SentenceTransformersEmbeddingsProvider,
)
from shifu.intelligence.providers.retrieval.sentence_transformers.sentence_transformers_mentor_faq_reranker_provider import (
    SentenceTransformersMentorFaqRerankerProvider,
)


def main() -> None:
    repository, catalog, close = build_mentor_index_dependencies()
    try:
        SentenceTransformersMentorFaqRerankerProvider(local_files_only=False).prepare()
        version = prepare_indexes(
            SentenceTransformersEmbeddingsProvider(local_files_only=False),
            repository,
            catalog,
            MentorResources(),
        )
        print(f'Mentor index activated: {version}')
    finally:
        close()


if __name__ == '__main__':
    main()

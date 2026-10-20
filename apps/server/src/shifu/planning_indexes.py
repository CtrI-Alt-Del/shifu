"""Application entry point for explicit, offline Planner index preparation."""

from shifu.composition.planning_dependencies import build_planning_index_dependencies
from shifu.intelligence.ai.data.planner_resources import PlannerResources
from shifu.intelligence.prepare_planning_indexes import prepare_indexes
from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
    SentenceTransformersEmbeddingsProvider,
)
from shifu.intelligence.providers.planning.text_preprocessing.spacy.spacy_planning_text_preprocessor_provider import (
    SpacyPlanningTextPreprocessorProvider,
)


def main() -> None:
    repository, catalog, close = build_planning_index_dependencies()
    try:
        resources = PlannerResources()
        version = prepare_indexes(
            SentenceTransformersEmbeddingsProvider(local_files_only=False),
            repository,
            catalog,
            resources,
            SpacyPlanningTextPreprocessorProvider(resources.manifest.negation),
        )
        print(f'Planner index activated: {version}')
    finally:
        close()


if __name__ == '__main__':
    main()

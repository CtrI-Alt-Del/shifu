"""Explicit offline preparation; never imported to rebuild an index on request."""

from shifu.intelligence.ai.data.mentor_resources import MentorResources
from shifu.intelligence.core.domain.structures.mentor_indexed_embedding import (
    MentorIndexedEmbedding,
)
from shifu.intelligence.core.interfaces.mentor_embeddings_provider import (
    MentorEmbeddingsProvider,
)
from shifu.intelligence.core.interfaces.mentor_embeddings_repository import (
    MentorEmbeddingsRepository,
)
from shifu.shared.core.interfaces.mentor_catalog_provider import MentorCatalogProvider


def prepare_indexes(
    embeddings: MentorEmbeddingsProvider,
    repository: MentorEmbeddingsRepository,
    catalog: MentorCatalogProvider,
    resources: MentorResources,
) -> str:
    projection = catalog.read_projection()
    resources.bind_catalog_version(projection)
    records: list[tuple[str, str, str, str]] = []
    for label, examples in resources.intents.items():
        records.extend(
            ('intents', label, str(index), text)
            for index, text in enumerate(dict.fromkeys(examples))
        )
    for answer in resources.answers:
        records.extend(
            ('answers', answer.id, str(index), text)
            for index, text in enumerate(
                dict.fromkeys([answer.question, *answer.variations])
            )
        )
    for entry in projection:
        if entry.kind not in {'skill', 'competency', 'material', 'activity'}:
            raise ValueError('Invalid Mentor catalog entry')
        records.append(
            (
                'curriculum',
                entry.reference_id,
                entry.source_version,
                ' '.join([entry.title, entry.description or '', *entry.concept_ids]),
            )
        )
    records = list(dict.fromkeys(records))
    # All corpus validation and inference finish before any database activation.
    vectors = embeddings.embed_passages(tuple(text for _, _, _, text in records))
    if len(vectors) != len(records) or any(
        len(vector) != resources.manifest.dimension for vector in vectors
    ):
        raise ValueError('Invalid Mentor embedding dimension')
    indexed = tuple(
        MentorIndexedEmbedding(
            corpus=corpus,
            reference_id=reference,
            variation_key=variation,
            vector=vector,
        )
        for (corpus, reference, variation, _), vector in zip(
            records, vectors, strict=True
        )
    )
    repository.prepare_version(resources.version, indexed)
    repository.activate_version(resources.version)
    return resources.version

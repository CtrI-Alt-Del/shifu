"""Explicit offline preparation; never imported to rebuild an index on request."""

from shifu.intelligence.ai.data.planner_resources import PlannerResources
from shifu.intelligence.core.domain.structures.planning_indexed_embedding import (
    PlanningIndexedEmbedding,
)
from shifu.intelligence.core.interfaces.mentor_embeddings_provider import (
    MentorEmbeddingsProvider,
)
from shifu.intelligence.core.interfaces.planning_embeddings_repository import (
    PlanningEmbeddingsRepository,
)
from shifu.intelligence.core.interfaces.planning_text_preprocessor_provider import (
    PlanningTextPreprocessorProvider,
)
from shifu.shared.core.interfaces.curriculum_catalog_provider import (
    CurriculumCatalogProvider,
)


def prepare_indexes(
    embeddings: MentorEmbeddingsProvider,
    repository: PlanningEmbeddingsRepository,
    catalog: CurriculumCatalogProvider,
    resources: PlannerResources,
    preprocessor: PlanningTextPreprocessorProvider,
) -> str:
    skills = catalog.list_skills()
    if not skills:
        raise ValueError('The Planner index needs at least one authorized Skill')
    resources.bind_catalog(skills)
    # The semantic text keeps stop words and inflections; only whitespace is normalized.
    passages = tuple(
        preprocessor.normalize(f'{skill.name}. {skill.description}') for skill in skills
    )
    # All inference finishes before any database write or activation.
    vectors = embeddings.embed_passages(passages)
    if len(vectors) != len(skills) or any(
        len(vector) != resources.manifest.dimension for vector in vectors
    ):
        raise ValueError('Invalid Planner embedding dimension')
    indexed = tuple(
        PlanningIndexedEmbedding(skill_id=skill.id, vector=vector)
        for skill, vector in zip(skills, vectors, strict=True)
    )
    repository.prepare_version(resources.version, indexed)
    repository.activate_version(resources.version)
    return resources.version

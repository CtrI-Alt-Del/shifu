from shifu.intelligence.core.domain.errors import PlanningIndexUnavailableError
from shifu.intelligence.core.domain.structures import (
    PlanningQuery,
    PlanningSkillCandidate,
    PlanningSkillRetrieval,
)
from shifu.intelligence.core.interfaces import PlanningSkillRetrievalProvider
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import CurriculumCatalogProvider


class RetrievePlanningSkillsUseCase:
    def __init__(
        self,
        retrieval: PlanningSkillRetrievalProvider,
        catalog: CurriculumCatalogProvider,
    ) -> None:
        self._retrieval = retrieval
        self._catalog = catalog

    def execute(self, query: PlanningQuery) -> PlanningSkillRetrieval:
        try:
            ranking = self._retrieval.retrieve(query)
        except PlanningIndexUnavailableError:
            raise
        except (ServiceUnavailableError, ValueError) as error:
            raise PlanningIndexUnavailableError from error

        # Only the authorized catalog describes a candidate; the index holds ids alone.
        skills = {skill.id: skill for skill in self._catalog.list_skills()}
        identifiers = [entry.skill_id for entry in ranking.entries]
        foundations = self._catalog.find_direct_foundations_for_many(identifiers)
        candidates = tuple(
            PlanningSkillCandidate(
                skill_id=entry.skill_id,
                name=skills[entry.skill_id].name,
                description=skills[entry.skill_id].description,
                foundation_skill_ids=tuple(
                    dict.fromkeys(
                        foundation.skill_id
                        for foundation in foundations.get(entry.skill_id, [])
                    )
                ),
                score=entry.score,
                lexical_rank=entry.lexical_rank,
                semantic_rank=entry.semantic_rank,
            )
            for entry in ranking.entries
            if entry.skill_id in skills
        )
        return PlanningSkillRetrieval(
            index_version=ranking.index_version,
            lexical_ranking=ranking.lexical_ranking,
            semantic_ranking=ranking.semantic_ranking,
            candidates=candidates,
        )

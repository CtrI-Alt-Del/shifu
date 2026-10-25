from typing import Protocol

from shifu.intelligence.core.domain.structures.planning_query import PlanningQuery
from shifu.intelligence.core.domain.structures.planning_skill_ranking import (
    PlanningSkillRanking,
)


class PlanningSkillRetrievalProvider(Protocol):
    def retrieve(self, query: PlanningQuery) -> PlanningSkillRanking:
        """Rank authorized Skills for the query against the active index."""
        ...

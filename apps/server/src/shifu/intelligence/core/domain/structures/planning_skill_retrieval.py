from shifu.intelligence.core.domain.structures.planning_skill_candidate import (
    PlanningSkillCandidate,
)
from shifu.intelligence.core.domain.structures.planning_skill_ranking import (
    CANDIDATE_LIMIT,
)
from shifu.shared.core.domain.structures import structure


@structure
class PlanningSkillRetrieval:
    index_version: str
    lexical_ranking: tuple[str, ...]
    semantic_ranking: tuple[str, ...]
    candidates: tuple[PlanningSkillCandidate, ...]

    def __post_init__(self) -> None:
        if not self.index_version:
            raise ValueError('A retrieval must name its index version.')
        if len(self.candidates) > CANDIDATE_LIMIT:
            raise ValueError('The retrieval exceeds the candidate limit.')
        identifiers = [candidate.skill_id for candidate in self.candidates]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError('A retrieval cannot repeat a Skill.')
        ordered = sorted(
            self.candidates,
            key=lambda candidate: (-candidate.score, candidate.skill_id),
        )
        if tuple(ordered) != self.candidates:
            raise ValueError('Candidates are ordered by score, then Skill id.')

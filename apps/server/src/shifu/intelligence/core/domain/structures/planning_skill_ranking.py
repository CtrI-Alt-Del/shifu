from shifu.intelligence.core.domain.structures.planning_skill_rank_entry import (
    PlanningSkillRankEntry,
)
from shifu.shared.core.domain.structures import structure

LEXICAL_LIMIT = 10
SEMANTIC_LIMIT = 10
CANDIDATE_LIMIT = 20


@structure
class PlanningSkillRanking:
    index_version: str
    lexical_ranking: tuple[str, ...]
    semantic_ranking: tuple[str, ...]
    entries: tuple[PlanningSkillRankEntry, ...]

    def __post_init__(self) -> None:
        if not self.index_version:
            raise ValueError('A ranking must name its index version.')
        for ranking, limit in (
            (self.lexical_ranking, LEXICAL_LIMIT),
            (self.semantic_ranking, SEMANTIC_LIMIT),
        ):
            if len(ranking) > limit:
                raise ValueError('A source ranking exceeds its candidate limit.')
            if len(set(ranking)) != len(ranking):
                raise ValueError('A source ranking cannot repeat a Skill.')
        if len(self.entries) > CANDIDATE_LIMIT:
            raise ValueError('The fused ranking exceeds the candidate limit.')
        identifiers = [entry.skill_id for entry in self.entries]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError('The fused ranking cannot repeat a Skill.')
        sources = set(self.lexical_ranking) | set(self.semantic_ranking)
        if any(identifier not in sources for identifier in identifiers):
            raise ValueError('A fused entry must come from a source ranking.')
        ordered = sorted(self.entries, key=lambda entry: (-entry.score, entry.skill_id))
        if tuple(ordered) != self.entries:
            raise ValueError('Fused entries are ordered by score, then Skill id.')

from shifu.learning.core.domain.structures.completed_skill import CompletedSkill
from shifu.learning.core.domain.structures.evolution_option import EvolutionOption
from shifu.learning.core.domain.structures.recent_mastery import RecentMastery
from shifu.learning.core.domain.structures.resume_item import ResumeItem
from shifu.learning.core.domain.structures.stage_distribution import StageDistribution
from shifu.learning.core.domain.structures.weekly_count import WeeklyCount
from shifu.shared.core.domain.structures import structure


@structure
class LearningPanorama:
    has_goals: bool
    completed_skill_count: int
    mastered_competency_count: int
    stage_distribution: StageDistribution
    resume_items: tuple[ResumeItem, ...]  # at most 3
    weekly_evaluated_activities: tuple[WeeklyCount, ...]  # exactly 8, oldest first
    evolution_options: tuple[EvolutionOption, ...]
    default_evolution_skill_experience_id: str | None
    completed_skills: tuple[CompletedSkill, ...]  # newest completion first
    recent_masteries: tuple[RecentMastery, ...]  # at most 5, newest first

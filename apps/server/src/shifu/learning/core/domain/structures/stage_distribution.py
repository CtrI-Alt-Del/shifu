from shifu.shared.core.domain.structures import structure


@structure
class StageDistribution:
    not_started: int
    diagnosing: int
    learning: int
    completed: int
    goal_count: int  # Objetivos containing at least one experience

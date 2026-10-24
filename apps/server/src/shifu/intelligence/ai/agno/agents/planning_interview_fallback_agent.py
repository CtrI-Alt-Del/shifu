from shifu.intelligence.ai.agno.agents.mentor_agent import MentorModelConfig
from shifu.intelligence.ai.agno.agents.planning_interview_agent import (
    PlanningInterviewAgent,
)


class PlanningInterviewFallbackAgent(PlanningInterviewAgent):
    """The same Planner interview on GPT-6 Luna, asked only after DeepSeek fails."""

    MODEL = MentorModelConfig(
        transport='openrouter',
        model_id='openai/gpt-6-luna',
        timeout_seconds=60.0,
        profile='planner-interview-fallback',
    )

from shifu.intelligence.ai.agno.agents.mentor_agent import MentorModelConfig
from shifu.intelligence.ai.agno.agents.planning_proposal_agent import (
    PlanningProposalAgent,
)


class PlanningProposalFallbackAgent(PlanningProposalAgent):
    """The same Planner proposal on GPT-6 Luna, asked only after DeepSeek fails."""

    MODEL = MentorModelConfig(
        transport='openrouter',
        model_id='openai/gpt-6-luna',
        timeout_seconds=60.0,
        profile='planner-proposal-fallback',
    )

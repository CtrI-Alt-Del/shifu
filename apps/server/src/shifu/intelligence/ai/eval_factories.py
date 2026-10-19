"""Reusable Intelligence AI constructors for synthetic quality evaluations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from shifu.intelligence.ai.agno.agents import (
    MentorAttachmentAnswerAgent,
    MentorAttachmentVisionAgent,
    MentorReviewerAgent,
    MentorTitleAgent,
)
from shifu.intelligence.providers.code_rubric_assessor_provider.jev_code_rubric_assessor_provider import (
    JevCodeRubricAssessorProvider,
)
from shifu.intelligence.providers.openrouter.mentor_answer_model_provider import (
    OpenrouterMentorAnswerModelProvider,
)
from shifu.intelligence.providers.openrouter.mentor_title_model_provider import (
    MentorTitleModelProvider,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError

_REAL_EVAL_MODEL_TIMEOUT_SECONDS = 20.0

if TYPE_CHECKING:
    import httpx
    from agno.models.base import Model

    from shifu.shared.settings import Settings


def build_mentor_title_eval_agent(
    settings: Settings, *, model: Model | None = None
) -> MentorTitleAgent:
    selected_model = (
        model
        if model is not None
        else MentorTitleModelProvider.build(
            settings,
            timeout_seconds=_REAL_EVAL_MODEL_TIMEOUT_SECONDS,
        )
    )
    if selected_model is None:
        raise ServiceUnavailableError('Mentor title generation is unavailable.')
    return MentorTitleAgent(selected_model)


def build_mentor_attachment_vision_eval_agent(
    settings: Settings, *, model: Model | None = None
) -> MentorAttachmentVisionAgent:
    selected_model = (
        model
        if model is not None
        else OpenrouterMentorAnswerModelProvider.build(settings, profile='vision')
    )
    if selected_model is None:
        raise ServiceUnavailableError('Mentor attachment vision is unavailable.')
    return MentorAttachmentVisionAgent(selected_model)


def build_process_mentor_response_eval_agents(
    settings: Settings,
    *,
    answer_model: Model | None = None,
    reviewer_model: Model | None = None,
) -> tuple[MentorAttachmentAnswerAgent, MentorReviewerAgent]:
    selected_answer_model = (
        answer_model
        if answer_model is not None
        else OpenrouterMentorAnswerModelProvider.build(settings, profile='primary')
    )
    selected_reviewer_model = (
        reviewer_model
        if reviewer_model is not None
        else OpenrouterMentorAnswerModelProvider.build(settings, profile='reviewer')
    )
    if selected_answer_model is None or selected_reviewer_model is None:
        raise ServiceUnavailableError('Mentor response generation is unavailable.')
    return (
        MentorAttachmentAnswerAgent(selected_answer_model),
        MentorReviewerAgent(selected_reviewer_model),
    )


def build_code_rubric_eval_provider(
    settings: Settings, *, client: httpx.Client
) -> JevCodeRubricAssessorProvider:
    return JevCodeRubricAssessorProvider(
        api_key=settings.openrouter_api_key,
        client=client,
        decisions_url=str(settings.openrouter_decisions_url),
        model=settings.jev_model,
    )

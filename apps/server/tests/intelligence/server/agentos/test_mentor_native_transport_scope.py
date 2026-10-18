from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from agno.agent import Agent

if TYPE_CHECKING:
    from agno.models.base import Model

from shifu.intelligence.ai.agno.agents.mentor_attachment_vision_agent import (
    MentorAttachmentVisionAgent,
)
from shifu.intelligence.ai.agno.models.mentor_openai_chat import (
    _FAILURE,  # pyright: ignore[reportPrivateUsage] - Verifies the agent's scoped transport boundary.
)
from shifu.intelligence.ai.agno.outputs import MentorAttachmentVisionOutput
from shifu.intelligence.ai.data.mentor_inference_usage import inference_guard_scope


def test_vision_agent_installs_native_transport_failure_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def initialize(_self: object, **_kwargs: object) -> None:
        return

    def run(_self: object, **_kwargs: object) -> SimpleNamespace:
        # MentorOpenAIChat reads this ContextVar while parsing every response.
        assert _FAILURE.get() is not None
        return SimpleNamespace(
            content=MentorAttachmentVisionOutput(legible=True, description='1/2'),
            metrics=None,
        )

    monkeypatch.setattr(Agent, '__init__', initialize)
    monkeypatch.setattr(Agent, 'run', run)
    agent = MentorAttachmentVisionAgent(cast('Model', object()))

    with inference_guard_scope(lambda: None):
        result = agent.analyze(
            b'private image bytes',
            media_type='image/png',
            attachment_id='01J00000000000000000000000',
            page_number=1,
        )

    assert result.legible is True
    assert result.description == '1/2'

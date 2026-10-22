from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING
from typing import ClassVar, Literal

from shifu.intelligence.ai.agno.models.mentor_openai_chat import MentorOpenAIChat
from shifu.intelligence.providers.openrouter.openrouter_telemetry import (
    emit_openrouter_event,
)

if TYPE_CHECKING:
    from agno.models.message import Message
    from agno.models.response import ModelResponse
    from agno.run.agent import RunOutput
    from agno.run.team import TeamRunOutput
    from pydantic import BaseModel

    from shifu.shared.settings import Settings
    from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider


class _TelemetryMentorOpenAIChat(MentorOpenAIChat):
    _telemetry_provider: TelemetryProvider | None = None

    def bind_telemetry(self, telemetry_provider: TelemetryProvider | None) -> None:
        self._telemetry_provider = telemetry_provider

    def invoke(
        self,
        messages: list[Message],
        assistant_message: Message,
        response_format: dict[str, object] | type[BaseModel] | None = None,
        tools: list[dict[str, object]] | None = None,
        tool_choice: str | dict[str, object] | None = None,
        run_response: RunOutput | TeamRunOutput | None = None,
        compress_tool_results: bool = False,
    ) -> ModelResponse:
        started_at = perf_counter()
        emit_openrouter_event(
            self._telemetry_provider,
            event='integration.operation.started',
        )
        try:
            result = super().invoke(
                messages=messages,
                assistant_message=assistant_message,
                response_format=response_format,
                tools=tools,
                tool_choice=tool_choice,
                run_response=run_response,
                compress_tool_results=compress_tool_results,
            )
        except Exception as error:
            emit_openrouter_event(
                self._telemetry_provider,
                event='integration.operation.failed',
                result='failure',
                duration_ms=max((perf_counter() - started_at) * 1000, 0.0),
                error_code='integration_failed',
                exception_type=type(error).__name__,
            )
            raise
        emit_openrouter_event(
            self._telemetry_provider,
            event='integration.operation.completed',
            result='success',
            duration_ms=max((perf_counter() - started_at) * 1000, 0.0),
        )
        return result


class OpenrouterMentorAnswerModelProvider:
    _BASE_URL: ClassVar[str] = 'https://openrouter.ai/api/v1'
    _TIMEOUT_SECONDS: ClassVar[float] = 30.0
    _MODEL_IDS: ClassVar[dict[str, str]] = {
        'primary': 'openai/gpt-6-luna',
        'reviewer': 'openai/gpt-6-luna',
        'fallback': 'deepseek/deepseek-v4.1-flash',
        'vision': 'openai/gpt-6-luna',
    }

    @classmethod
    def build(
        cls,
        settings: Settings,
        *,
        profile: Literal['primary', 'fallback', 'reviewer', 'vision'] = 'primary',
        telemetry_provider: TelemetryProvider | None = None,
    ) -> MentorOpenAIChat | None:
        if (
            not settings.openrouter_api_key
            or not settings.openrouter_prompt_logging_disabled
        ):
            return None
        model = _TelemetryMentorOpenAIChat(
            id=cls._MODEL_IDS[profile],
            api_key=settings.openrouter_api_key,
            base_url=cls._BASE_URL,
            timeout=cls._TIMEOUT_SECONDS,
            max_retries=0,
            retries=0,
            retry_with_guidance=False,
            retry_with_guidance_limit=0,
            strict_output=True,
            store=False,
            extra_body={
                'provider': {
                    'zdr': True,
                    'data_collection': 'deny',
                    'require_parameters': True,
                    'allow_fallbacks': False,
                }
            },
        )
        model.bind_telemetry(telemetry_provider)
        return model

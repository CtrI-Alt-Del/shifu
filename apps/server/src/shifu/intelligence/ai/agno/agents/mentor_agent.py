"""The base of every Mentor agent: its model config, the bounded OpenRouter
transport that preserves native failures and usage receipts, and the Agent
settings all Mentor agents share."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, ClassVar, Literal, assert_never

from agno.agent import Agent
from agno.exceptions import ModelProviderError
from agno.models.openai import OpenAIChat
from agno.utils import log as agno_logging
from pydantic import BaseModel, ValidationError

from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.settings import Settings, get_settings

if TYPE_CHECKING:
    from collections.abc import Generator
    from agno.models.base import Model
    from agno.models.message import Message
    from agno.models.response import ModelResponse
    from agno.run.agent import RunOutput
    from agno.run.team import TeamRunOutput
    from openai.types.chat import ChatCompletion

_OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'


@dataclass(frozen=True, slots=True)
class MentorModelConfig:
    """Which model one Mentor agent runs on, and how its transport is bounded.

    Each agent class declares its own config. The transport names the model
    gateway, `profile` labels usage records and test transports, and
    `prompt_logging_gate` names the setting that must confirm prompt logging is
    disabled before the agent may run.
    """

    transport: Literal['openrouter']
    model_id: str
    timeout_seconds: float
    profile: str
    prompt_logging_gate: Literal['openrouter', 'mentor_title'] = 'openrouter'


# Transport failures: Agno turns a provider error into an error result and drops
# the original exception. The scope below keeps the error, its cause and the
# token receipt of an HTTP-200 error envelope, so agents can raise typed errors
# and still charge the attempt.


@dataclass
class _TransportFailure:
    error: ModelProviderError | None = None
    cause: BaseException | None = None
    used_tokens: int | None = None

    def raise_if_failed(self) -> None:
        if self.error is not None:
            self.error.__cause__ = self.cause
            raise self.error


_FAILURE: ContextVar[_TransportFailure] = ContextVar('mentor_native_transport_failure')


class _MentorPrivateLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        del record
        return _FAILURE.get(None) is None


_PRIVATE_LOG_FILTER = _MentorPrivateLogFilter()


def configure_mentor_sdk_logging() -> None:
    """Install contextual protection without replacing SDK logger configuration."""
    loggers = {
        agno_logging.agent_logger,
        agno_logging.team_logger,
        agno_logging.workflow_logger,
        agno_logging.logger,
        logging.getLogger('openai._base_client'),
    }
    for logger in loggers:
        logger.addFilter(_PRIVATE_LOG_FILTER)


@contextmanager
def mentor_transport_failure_scope() -> Generator[_TransportFailure]:
    failure = _TransportFailure()
    token = _FAILURE.set(failure)
    try:
        yield failure
    except ModelProviderError as error:
        if error is failure.error:
            error.__cause__ = failure.cause
        raise
    finally:
        failure.error = None
        failure.cause = None
        failure.used_tokens = None
        _FAILURE.reset(token)


class _MentorOpenAIChat(OpenAIChat):
    def _parse_provider_response(
        self,
        response: ChatCompletion,
        response_format: dict[str, object] | type[BaseModel] | None = None,
    ) -> ModelResponse:
        # Retain only numeric consumption before native parsing rejects an
        # HTTP-200 error envelope, discarding its authenticated usage receipt.
        failure = _FAILURE.get()
        usage = response.usage
        if usage is not None:
            values = (usage.prompt_tokens, usage.completion_tokens, usage.total_tokens)
            if all(type(value) is int and value >= 0 for value in values):
                prompt, completion, total = values
                if prompt + completion == total:
                    failure.used_tokens = total
        return super()._parse_provider_response(  # pyright: ignore[reportUnknownMemberType] - Native SDK response_format uses an unparameterized Dict.
            response, response_format=response_format
        )

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
        failure = _FAILURE.get()
        failure.error = None
        failure.cause = None
        failure.used_tokens = None
        try:
            return super().invoke(  # pyright: ignore[reportUnknownMemberType] - Native SDK response_format uses an unparameterized Dict.
                messages=messages,
                assistant_message=assistant_message,
                response_format=response_format,
                tools=tools,
                tool_choice=tool_choice,
                run_response=run_response,
                compress_tool_results=compress_tool_results,
            )
        except ModelProviderError as error:
            failure.error = error
            failure.cause = error.__cause__
            raise


class MentorAgent(Agent):
    """Base for every Mentor agent: resolves its own model and runs privately.

    A subclass declares `MODEL` and passes only its name, instructions and output
    schema. Tools, retries, telemetry and history are off for all of them. When the
    model is not enabled the agent is built without one; the registry composes an
    unavailable double in that case, and the evals assign a synthetic model.
    """

    MODEL: ClassVar[MentorModelConfig]

    def __init__(
        self,
        *,
        name: str,
        instructions: str,
        output_schema: type[BaseModel],
        description: str | None = None,
    ) -> None:
        configure_mentor_sdk_logging()
        super().__init__(  # pyright: ignore[reportUnknownMemberType] - Agno lacks complete SDK stubs.
            name=name,
            description=description,
            model=self.build_model() if self.enabled() else None,
            instructions=instructions,
            output_schema=output_schema,
            tools=[],
            retries=0,
            debug_mode=False,
            telemetry=False,
            store_history_messages=False,
            add_history_to_context=False,
            read_chat_history=False,
            read_tool_call_history=False,
            store_tool_messages=False,
            store_events=False,
        )

    @classmethod
    def enabled(cls) -> bool:
        """True when the transport has its credential and prompt logging is off."""
        settings = cls._settings()
        if settings is None:
            return False
        match cls.MODEL.transport:
            case 'openrouter':
                return bool(
                    settings.openrouter_api_key
                ) and cls._prompt_logging_disabled(settings)
            case _:
                assert_never(cls.MODEL.transport)

    @classmethod
    def build_model(cls, config: MentorModelConfig | None = None) -> Model:
        """Resolve `config` (the class config by default) into a bounded model."""
        config = cls.MODEL if config is None else config
        settings = cls._settings()
        api_key = settings.openrouter_api_key if settings is not None else None
        if not api_key or not cls.enabled():
            raise ServiceUnavailableError(
                f'Mentor model {config.profile} is unavailable.'
            )
        match config.transport:
            case 'openrouter':
                return _MentorOpenAIChat(
                    id=config.model_id,
                    api_key=api_key,
                    base_url=_OPENROUTER_BASE_URL,
                    timeout=config.timeout_seconds,
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
            case _:
                assert_never(config.transport)

    @staticmethod
    def _settings() -> Settings | None:
        # Without a loadable environment no model is enabled; the registry then
        # composes the unavailable doubles instead of failing at import time.
        try:
            return get_settings()
        except ValidationError:
            return None

    @classmethod
    def _prompt_logging_disabled(cls, settings: Settings) -> bool:
        match cls.MODEL.prompt_logging_gate:
            case 'openrouter':
                return settings.openrouter_prompt_logging_disabled
            case 'mentor_title':
                return settings.mentor_title_prompt_logging_disabled
            case _:
                assert_never(cls.MODEL.prompt_logging_gate)

"""Preserve native transport failures across Agno's error-result boundary."""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import logging

from agno.exceptions import ModelProviderError
from agno.models.message import Message
from agno.models.openai import OpenAIChat
from agno.models.response import ModelResponse
from agno.run.agent import RunOutput
from agno.run.team import TeamRunOutput
from agno.utils import log as agno_logging
from openai.types.chat import ChatCompletion
from pydantic import BaseModel


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


class MentorOpenAIChat(OpenAIChat):
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

from collections.abc import Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar

from shifu.intelligence.core.domain.structures.mentor_inference_usage import (
    MentorInferenceUsage,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError


_SINK: ContextVar[Callable[[MentorInferenceUsage], None]] = ContextVar(
    'mentor_usage_sink'
)
_PREFIX: ContextVar[str] = ContextVar('mentor_usage_prefix', default='')
_GUARD: ContextVar[Callable[[], None]] = ContextVar('mentor_inference_guard')


@contextmanager
def inference_guard_scope(guard: Callable[[], None] | None) -> Generator[None]:
    if guard is None:
        raise ServiceUnavailableError('A autorização do Mentor está indisponível.')
    token = _GUARD.set(guard)
    try:
        yield
    finally:
        _GUARD.reset(token)


def assert_inference_ready() -> None:
    _GUARD.get()()


@contextmanager
def inference_usage_scope(
    prefix: str,
    recorder: Callable[[MentorInferenceUsage], None] | None,
) -> Generator[None]:
    if recorder is None:
        raise ServiceUnavailableError('O registro de uso do Mentor está indisponível.')
    sink_token = _SINK.set(recorder)
    prefix_token = _PREFIX.set(prefix)
    try:
        yield
    finally:
        _SINK.reset(sink_token)
        _PREFIX.reset(prefix_token)


def report_inference_usage(
    call: str,
    profile: str,
    used_tokens: int | None,
    *,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cost_usd: float | None = None,
) -> None:
    _SINK.get()(
        MentorInferenceUsage(
            call_key=f'{_PREFIX.get()}:{call}',
            profile=profile,
            used_tokens=used_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )
    )

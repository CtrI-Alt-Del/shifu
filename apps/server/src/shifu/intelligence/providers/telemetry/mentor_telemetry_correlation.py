"""Correlation context shared by Mentor telemetry adapters."""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

_CORRELATION: ContextVar[str | None] = ContextVar(
    'mentor_telemetry_correlation', default=None
)


@contextmanager
def mentor_telemetry_correlation() -> Generator[None]:
    token = _CORRELATION.set(str(uuid4()))
    try:
        yield
    finally:
        _CORRELATION.reset(token)


def current_mentor_telemetry_correlation() -> str | None:
    return _CORRELATION.get()

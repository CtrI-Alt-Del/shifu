"""Shared AgentOS input envelopes and ContextVar plumbing for the Learning
evaluation workflows (code and translation), which share an identical
official-run/transient-handoff input protocol and execution bookkeeping.

Each workflow's own `Step` executors must keep globally unique bare method
names, since Agno's registry resolves durable step executors by bare name at
rehydration; only this non-executor support logic is shared here.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shifu.shared.core.domain.errors import ServiceUnavailableError

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextvars import ContextVar

    from agno.workflow.types import StepInput

    from shifu.shared.messaging.agentos.agentos_handoff_store import (
        AgentOSHandoffStore,
    )


class OfficialRunInput(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    attempt_id: str = Field(min_length=1, max_length=64)
    run_id: str = Field(min_length=1, max_length=64)


class HandoffAssessmentInput(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    handoff_ref: str = Field(min_length=20, max_length=128)


def safe_native_input(raw: object, unavailable_message: str) -> str:
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            raise ServiceUnavailableError(unavailable_message) from None
    else:
        value = raw
    try:
        official = OfficialRunInput.model_validate(value, strict=True)
        return official.model_dump_json()
    except ValidationError:
        try:
            handoff = HandoffAssessmentInput.model_validate(value, strict=True)
            return handoff.model_dump_json()
        except ValidationError:
            raise ServiceUnavailableError(unavailable_message) from None


def execution_for_step[ExecutionT](
    execution_var: ContextVar[ExecutionT | None],
    step_input: StepInput,
    make_execution: Callable[[object], ExecutionT],
) -> ExecutionT:
    execution = execution_var.get()
    if execution is None:
        execution = make_execution(step_input.input)
        execution_var.set(execution)
    return execution


def complete_unavailable(
    handoffs: AgentOSHandoffStore, reference: str, capability: str
) -> None:
    try:
        handoffs.complete(reference, capability=capability, result_value='unavailable')
    except KeyError:
        return

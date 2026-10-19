"""Export allowlisted operational agent metadata to Langfuse."""

from __future__ import annotations

from math import isfinite
from typing import TYPE_CHECKING, ClassVar, Literal
from uuid import UUID, uuid4, uuid5

if TYPE_CHECKING:
    from langfuse import Langfuse

SafeOutcome = Literal['passed', 'failed', 'abstained', 'cancelled']


class LangfuseTelemetryProvider:
    """Export operational metadata with no private inputs or outputs."""

    _SAFE_COUNTS: ClassVar[frozenset[str]] = frozenset(
        {'blocks', 'observations', 'matches', 'inference_requests', 'criteria'}
    )

    def __init__(
        self,
        module: Literal['intelligence', 'learning'],
        client: Langfuse | None = None,
    ) -> None:
        self._module: Literal['intelligence', 'learning'] = module
        self._client: Langfuse | None = client
        self._trace_namespace: UUID = uuid4()

    def record(
        self,
        *,
        stage: str,
        outcome: SafeOutcome,
        duration_ms: float,
        correlation_id: str | None = None,
        model_profile: str | None = None,
        tokens: int | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float | None = None,
        counts: dict[str, int] | None = None,
    ) -> None:
        if self._client is None:
            return
        try:
            attributes = self._attributes(
                stage=stage,
                outcome=outcome,
                duration_ms=duration_ms,
                model_profile=model_profile,
                tokens=tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                counts=counts,
            )
            usage: dict[str, int] = {
                target: int(attributes[source])
                for source, target in (
                    ('tokens', 'total'),
                    ('input_tokens', 'input'),
                    ('output_tokens', 'output'),
                )
                if source in attributes
            }
            cost = (
                {'total': float(attributes['cost_usd'])}
                if 'cost_usd' in attributes
                else None
            )
            stage = str(attributes['stage'])
            trace_id = self._safe_trace_id(correlation_id)
            level: Literal['ERROR', 'DEFAULT'] = (
                'ERROR' if attributes['outcome'] == 'failed' else 'DEFAULT'
            )
            if stage == 'inference':
                observation = self._client.start_observation(
                    trace_context={'trace_id': trace_id},
                    name=f'{self._module}.{stage}',
                    as_type='generation',
                    metadata=attributes,
                    level=level,
                    model=str(attributes['model_profile'])
                    if 'model_profile' in attributes
                    else None,
                    usage_details=usage or None,
                    cost_details=cost,
                )
            else:
                observation = self._client.start_observation(
                    trace_context={'trace_id': trace_id},
                    name=f'{self._module}.{stage}',
                    as_type='span',
                    metadata=attributes,
                    level=level,
                )
            # SDK v3's public API cannot backdate observation starts. Preserve
            # measured workflow duration as metadata, without inventing a timeline.
            # No current observation context or automatic capture is activated.
            observation.end()
        except Exception:  # noqa: BLE001 - monitoring never affects business work.
            return

    def bind(self, client: Langfuse | None) -> None:
        """Bind the client owned and closed by application lifespan."""
        self._client = client

    def _attributes(
        self,
        *,
        stage: str,
        outcome: SafeOutcome,
        duration_ms: float,
        model_profile: str | None,
        tokens: int | None,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_usd: float | None,
        counts: dict[str, int] | None,
    ) -> dict[str, str | int | float]:
        if stage not in {
            'classify',
            'retrieve',
            'title',
            'route',
            'prepare',
            'infer',
            'review',
            'publish',
            'evaluate',
            'inference',
        }:
            stage = 'workflow'
        if (
            isinstance(duration_ms, bool)
            or not isfinite(duration_ms)
            or duration_ms < 0
        ):
            duration_ms = 0
        attributes: dict[str, str | int | float] = {
            'module': self._module,
            'stage': stage,
            'outcome': outcome
            if outcome in {'passed', 'failed', 'abstained', 'cancelled'}
            else 'failed',
            'duration_ms': int(duration_ms),
        }
        allowed_profiles = {
            'local',
            'openrouter-title',
            'jev-rubric',
            'jev-review',
            'mentor-writer',
            'mentor-reviewer',
            'mentor-attachment-vision',
            'mentor-attachment-answer',
        }
        if model_profile in allowed_profiles:
            attributes['model_profile'] = model_profile
        for name, value in (
            ('tokens', tokens),
            ('input_tokens', input_tokens),
            ('output_tokens', output_tokens),
        ):
            if type(value) is int and value >= 0:
                attributes[name] = value
        if (
            not isinstance(cost_usd, bool)
            and isinstance(cost_usd, (int, float))
            and isfinite(cost_usd)
            and cost_usd >= 0
        ):
            attributes['cost_usd'] = cost_usd
        if counts is not None:
            attributes.update(
                {
                    name: count
                    for name, count in counts.items()
                    if name in LangfuseTelemetryProvider._SAFE_COUNTS
                    and type(count) is int
                    and count >= 0
                }
            )
        return attributes

    def _safe_trace_id(self, value: str | None) -> str:
        if value is not None:
            try:
                # Even UUID-shaped business IDs must not leave the process.
                return uuid5(self._trace_namespace, UUID(value).hex).hex
            except (ValueError, AttributeError, TypeError):
                pass
        return uuid4().hex

"""Write filtered spans directly to a module's pre-migrated AgentOS tables."""

from datetime import UTC, datetime, timedelta
from math import isfinite
from typing import Literal
from uuid import UUID, uuid4

from agno.db.postgres import PostgresDb
from agno.tracing.schemas import Span, Trace

SafeOutcome = Literal['passed', 'failed']


class AgentOSObservability:
    """Persist only allowlisted operational metadata, never prompts or outputs."""

    _SAFE_COUNTS = frozenset(
        {'blocks', 'observations', 'matches', 'inference_requests', 'criteria'}
    )

    def __init__(
        self, module: Literal['intelligence', 'learning'], db: PostgresDb
    ) -> None:
        self._module = module
        self._db = db

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
        now = datetime.now(UTC)
        trace_id = self._safe_trace_id(correlation_id)
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
        stage = str(attributes['stage'])
        duration_ms = int(attributes['duration_ms'])
        started_at = now - timedelta(milliseconds=duration_ms)

        try:
            trace = Trace(
                trace_id=trace_id,
                name=f'shifu-{self._module}-{stage}',
                status=outcome,
                start_time=started_at,
                end_time=now,
                duration_ms=int(duration_ms),
                total_spans=1,
                error_count=1 if outcome == 'failed' else 0,
                run_id=None,
                session_id=None,
                user_id=None,
                agent_id=None,
                team_id=None,
                workflow_id=None,
                created_at=now,
            )
            span = Span(
                span_id=uuid4().hex,
                trace_id=trace_id,
                parent_span_id=None,
                name=f'{self._module}.{stage}',
                span_kind='INTERNAL',
                status_code='OK' if outcome == 'passed' else 'ERROR',
                status_message=None,
                start_time=started_at,
                end_time=now,
                duration_ms=int(duration_ms),
                attributes=attributes,
                created_at=now,
            )
            self._db.upsert_trace(trace)
            self._db.create_span(span)
        except Exception:  # noqa: BLE001 - telemetry must not affect business work.
            return

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
        if not isfinite(duration_ms) or duration_ms < 0:
            duration_ms = 0
        attributes: dict[str, str | int | float] = {
            'module': self._module,
            'stage': stage,
            'outcome': outcome,
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
            if value is not None and value >= 0:
                attributes[name] = value
        if cost_usd is not None and isfinite(cost_usd) and cost_usd >= 0:
            attributes['cost_usd'] = cost_usd
        if counts is not None:
            attributes.update(
                {
                    name: count
                    for name, count in counts.items()
                    if name in AgentOSObservability._SAFE_COUNTS and count >= 0
                }
            )
        return attributes

    @staticmethod
    def _safe_trace_id(value: str | None) -> str:
        if value is not None:
            try:
                return UUID(value).hex
            except ValueError:
                pass
        return uuid4().hex

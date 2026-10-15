from __future__ import annotations

from typing import TYPE_CHECKING, cast
from uuid import UUID

import pytest

from shifu.intelligence.core.domain.structures import MentorReviewResult
from shifu.intelligence.providers.telemetry.agentos.agentos_mentor_telemetry_provider import (
    AgentOSMentorTelemetryProvider,
)
from shifu.intelligence.providers.telemetry.mentor_telemetry_correlation import (
    current_mentor_telemetry_correlation,
    mentor_telemetry_correlation,
)
from shifu.shared.messaging.agentos.agentos_observability import AgentOSObservability

if TYPE_CHECKING:
    from agno.db.postgres import PostgresDb
    from agno.tracing.schemas import Span, Trace


class _Database:
    def __init__(self, *, fail_trace: bool = False, fail_span: bool = False) -> None:
        self.traces: list[Trace] = []
        self.spans: list[Span] = []
        self._fail_trace = fail_trace
        self._fail_span = fail_span

    def upsert_trace(self, trace: Trace) -> None:
        if self._fail_trace:
            raise RuntimeError('telemetry database unavailable')
        self.traces.append(trace)

    def create_span(self, span: Span) -> None:
        if self._fail_span:
            raise RuntimeError('span database unavailable')
        self.spans.append(span)


class TestAgentOSObservability:
    def test_record_persists_allowlisted_operational_metadata_only(self) -> None:
        database = _Database()
        trace_id = 'd5d22836-752f-4ec8-9bd0-dd0a1cc67028'
        observability = AgentOSObservability(
            'intelligence', cast('PostgresDb', database)
        )

        observability.record(
            stage='prepare',
            outcome='passed',
            duration_ms=12.8,
            correlation_id=trace_id,
            model_profile='mentor-attachment-vision',
            tokens=12,
            input_tokens=-1,
            output_tokens=8,
            cost_usd=0.05,
            counts={'observations': 2, 'criteria': 3, 'prompt': 9, 'blocks': -1},
        )

        assert len(database.traces) == len(database.spans) == 1
        trace = database.traces[0]
        span = database.spans[0]
        assert trace.trace_id == UUID(trace_id).hex
        assert trace.name == 'shifu-intelligence-prepare'
        assert trace.status == 'passed'
        attributes = span.attributes
        assert attributes == {
            'module': 'intelligence',
            'stage': 'prepare',
            'outcome': 'passed',
            'duration_ms': 12,
            'model_profile': 'mentor-attachment-vision',
            'tokens': 12,
            'output_tokens': 8,
            'cost_usd': 0.05,
            'observations': 2,
            'criteria': 3,
        }
        assert span.trace_id == UUID(trace_id).hex

    def test_record_sanitizes_invalid_metrics_and_does_not_break_work_on_write_errors(
        self,
    ) -> None:
        database = _Database(fail_trace=True)
        observability = AgentOSObservability('learning', cast('PostgresDb', database))

        observability.record(
            stage='unapproved-stage',
            outcome='failed',
            duration_ms=float('nan'),
            correlation_id='private-correlation-value',
            model_profile='unapproved-model',
            tokens=-1,
            cost_usd=float('inf'),
            counts={'matches': 1, 'prompt': 8},
        )

        assert database.spans == []

    def test_record_ignores_span_write_failures_after_trace_write(self) -> None:
        database = _Database(fail_span=True)
        observability = AgentOSObservability(
            'intelligence', cast('PostgresDb', database)
        )

        observability.record(
            stage='review',
            outcome='passed',
            duration_ms=1,
            correlation_id='not-a-uuid',
        )

        assert len(database.traces) == 1
        assert database.spans == []
        assert database.traces[0].trace_id != 'not-a-uuid'

    def test_mentor_telemetry_records_safe_correlated_events_and_failure_outcomes(
        self,
    ) -> None:
        database = _Database()
        observability = AgentOSObservability(
            'intelligence', cast('PostgresDb', database)
        )
        telemetry = AgentOSMentorTelemetryProvider(observability)
        assert current_mentor_telemetry_correlation() is None

        with mentor_telemetry_correlation():
            correlation_id = current_mentor_telemetry_correlation()
            assert correlation_id is not None
            with telemetry.scope('route'):
                pass
            telemetry.record_inference('mentor-attachment-answer', 9, 4, 5, 0.02)
            telemetry.emit(
                'prepare',
                correlation_id='untrusted-id',
                profile='unapproved-profile',
                duration_ms=4.5,
                counts={'blocks': 2, 'prompt': 99},
                outcome='abstained',
            )
            telemetry.record_answer(
                attempt_id='private-attempt',
                block_key='private-block',
                version=3,
                correlation_id='untrusted-id',
                answer='private answer text',
            )
            telemetry.record_review(
                attempt_id='private-attempt',
                block_key='private-block',
                version=3,
                correlation_id='untrusted-id',
                answer='private answer text',
                review=MentorReviewResult(
                    approved=True,
                    criteria=(('privacy_access', 'approved', None),),
                    correction=None,
                ),
            )

            with (
                pytest.raises(RuntimeError, match='controlled failure'),
                telemetry.scope('unapproved-stage'),
            ):
                raise RuntimeError('controlled failure')

        assert current_mentor_telemetry_correlation() is None
        assert len(database.traces) == len(database.spans) == 6
        assert all(
            span.trace_id == correlation_id.replace('-', '') for span in database.spans
        )
        assert database.spans[0].attributes['stage'] == 'route'
        assert database.spans[0].attributes['outcome'] == 'passed'
        assert (
            database.spans[1].attributes['model_profile'] == 'mentor-attachment-answer'
        )
        assert 'unapproved-profile' not in repr(database.spans)
        assert 'prompt' not in database.spans[2].attributes
        assert database.spans[2].attributes['outcome'] == 'passed'
        assert database.spans[3].attributes['stage'] == 'infer'
        assert database.spans[4].attributes['stage'] == 'review'
        assert database.spans[4].attributes['criteria'] == 1
        assert database.spans[5].attributes['stage'] == 'workflow'
        assert database.spans[5].attributes['outcome'] == 'failed'
        assert 'private answer text' not in repr(database.spans)

    def test_mentor_telemetry_is_optional_and_correlation_scope_restores_context(
        self,
    ) -> None:
        telemetry = AgentOSMentorTelemetryProvider()
        telemetry.record_inference('local', 1, 1, 0, None)
        telemetry.emit(
            'route',
            correlation_id='correlation',
            profile='local',
            duration_ms=1,
            counts={},
            outcome='cancelled',
        )
        telemetry.record_answer(
            attempt_id='attempt',
            block_key='block',
            version=1,
            correlation_id='correlation',
            answer='private',
        )
        telemetry.bind(None)
        assert current_mentor_telemetry_correlation() is None
        with mentor_telemetry_correlation():
            assert current_mentor_telemetry_correlation() is not None
        assert current_mentor_telemetry_correlation() is None

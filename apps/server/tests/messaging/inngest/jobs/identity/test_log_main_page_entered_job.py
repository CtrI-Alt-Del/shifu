import dataclasses
import json
from pathlib import Path
from typing import TYPE_CHECKING

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.identity.core.domain.events import (
    MainPageEnteredEvent,
    MainPageEnteredPayload,
)
from tests.fixtures.telemetry_boundary_fixture import (
    read_job_telemetry,
    telemetry_inngest_app_target,
)

inngest_app_target = telemetry_inngest_app_target


if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture


class TestLogMainPageEnteredJob:
    def test_emits_a_completion_event_for_the_registered_logging_job(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        from shifu.fakers.shared.id_provider_faker import IdProviderFaker
        from shifu.identity.core.domain.events import (
            MainPageEnteredEvent,
            MainPageEnteredPayload,
        )

        event_id = IdProviderFaker().generate()

        event = MainPageEnteredEvent(
            payload=MainPageEnteredPayload(
                event_id=event_id,
                account_id='01SHF000000000000000000001',
                occurred_at='2026-09-16T20:00:00+00:00',
            )
        )

        inngest_fixture.publish(
            event.name,
            {
                'event_id': event.payload.event_id,
                'account_id': event.payload.account_id,
                'occurred_at': event.payload.occurred_at,
            },
            event.payload.event_id,
        )
        log_line = inngest_fixture.wait_for_log(
            f'"event":"job.completed","event_id":"{event_id}"', timeout=90
        )

        assert '"job":"identity.log_main_page_entered"' in log_line
        completed = json.loads(log_line)
        assert completed['attempt'] == 1
        assert isinstance(completed['run_id'], str) and completed['run_id']
        assert completed['event_id'] == event_id
        assert completed['result'] == 'success'
        assert 'account_id' not in completed
        events = [
            entry
            for entry in read_job_telemetry(inngest_fixture.runtime_environment)
            if entry.get('event_id') == event_id
        ]
        names = [entry['event'] for entry in events]
        assert names[0] == 'job.started'
        assert names[-1] == 'job.completed'
        assert names.count('job.completed') == 1
        assert set(names) == {'job.started', 'job.completed'}
        assert all(entry.get('run_id') == completed['run_id'] for entry in events)
        assert all(
            entry.get('job') == 'identity.log_main_page_entered' for entry in events
        )
        assert all(entry.get('attempt') == 1 for entry in events)
        assert event.payload.account_id not in str(events)
        assert 'secret' not in str(events)

    def test_collector_failure_does_not_prevent_registered_job_completion(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        assert inngest_fixture.runtime_environment is not None
        control = Path(
            inngest_fixture.runtime_environment['SHIFU_TEST_TELEMETRY_CONTROL']
        )
        event = _event()
        control.write_text('collector-failure')
        try:
            inngest_fixture.publish(
                event.name, dataclasses.asdict(event.payload), event.payload.event_id
            )
            inngest_fixture.wait_for_log(
                f'"event":"job.completed","event_id":"{event.payload.event_id}"',
                timeout=90,
            )
            events = [
                entry
                for entry in read_job_telemetry(inngest_fixture.runtime_environment)
                if entry.get('event_id') == event.payload.event_id
            ]
        finally:
            control.unlink(missing_ok=True)

        names = [entry['event'] for entry in events]
        assert names[0] == 'job.started'
        assert names[-1] == 'job.completed'
        assert names.count('job.completed') == 1
        assert set(names) == {'job.started', 'job.completed'}
        assert events[-1].get('result') == 'success'
        completed = events[-1]
        assert isinstance(completed.get('run_id'), str) and completed.get('run_id')
        assert all(entry.get('run_id') == completed.get('run_id') for entry in events)
        assert all(entry.get('event_id') == event.payload.event_id for entry in events)
        assert all(
            entry.get('job') == 'identity.log_main_page_entered' for entry in events
        )
        assert all(entry.get('attempt') == 1 for entry in events)
        assert event.payload.account_id not in str(events)

    def test_rejects_extra_payload_fields_without_copying_private_payload_to_telemetry(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        event = _event()
        payload: dict[str, object] = {
            **dataclasses.asdict(event.payload),
            'secret': 'must-not-be-copied',
        }
        inngest_fixture.publish(event.name, payload, event.payload.event_id)
        inngest_fixture.wait_for_log(
            f'"event":"job.failed","event_id":"{event.payload.event_id}"', timeout=90
        )
        events = [
            entry
            for entry in read_job_telemetry(inngest_fixture.runtime_environment)
            if entry.get('event_id') == event.payload.event_id
        ]
        assert events[0]['event'] == 'job.started'
        assert events[-1]['event'] == 'job.failed'
        assert all(entry['event'] != 'job.completed' for entry in events)
        assert 'must-not-be-copied' not in str(events)
        assert event.payload.account_id not in str(events)


def _event() -> MainPageEnteredEvent:
    event_id = IdProviderFaker().generate()
    return MainPageEnteredEvent(
        payload=MainPageEnteredPayload(
            event_id=event_id,
            account_id='01SHF000000000000000000001',
            occurred_at='2026-09-16T20:00:00+00:00',
        )
    )

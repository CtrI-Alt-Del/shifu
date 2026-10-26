import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture


@pytest.fixture(scope='session')
def inngest_app_target() -> tuple[str, bool]:
    return 'tests.shared.job_telemetry_application:create_app', True


class TestLogMainPageEnteredJob:
    def test_emits_a_completion_event_for_the_registered_logging_job(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        from shifu.identity.core.domain.events import (
            MainPageEnteredEvent,
            MainPageEnteredPayload,
        )
        from shifu.fakers.shared.id_provider_faker import IdProviderFaker

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
        started_line = inngest_fixture.wait_for_log(
            f'"event":"job.started","event_id":"{event_id}"', timeout=30
        )
        started = json.loads(started_line)
        assert completed['run_id'] == started['run_id']
        assert completed['run_id']
        assert completed['event_id'] == started['event_id'] == event_id
        assert completed['attempt'] >= 1
        assert started['attempt'] >= 1
        assert completed['result'] == 'success'
        assert 'account_id' not in completed
        assert event.payload.account_id not in log_line
        # The fixture sink raises after recording every job.started event.
        # Completion through durable execution proves instrumentation cannot fail it.

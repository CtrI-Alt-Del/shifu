from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture


class TestLogMainPageEnteredJob:
    def test_publishes_a_canonical_event_to_the_registered_logging_job(
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
        log_line = inngest_fixture.wait_for_log('identity.main_page_entered')

        assert event.payload.event_id in log_line
        assert event.payload.account_id in log_line
        assert event.payload.occurred_at in log_line

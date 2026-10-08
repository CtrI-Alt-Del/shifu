"""Real-runtime coverage for CA-01: profile creation on account activation."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from shifu.gamification.database.sqlalchemy.models import GamificationProfileModel
from shifu.identity.core.domain.events import (
    AccountActivatedEvent,
    AccountActivatedPayload,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tests.fixtures.inngest_fixture import InngestFixture


class TestCreateProfileOnAccountActivatedJob:
    def test_should_create_exactly_one_profile_and_be_idempotent_under_redelivery(
        self,
        inngest_fixture: 'InngestFixture',
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        activated_at = (
            datetime(2026, 1, 1, tzinfo=UTC).isoformat().replace('+00:00', 'Z')
        )
        event = AccountActivatedEvent(
            payload=AccountActivatedPayload(
                account_id=account_id,
                activated_at=activated_at,
            )
        )

        inngest_fixture.publish(
            event.name,
            {
                'account_id': event.payload.account_id,
                'activated_at': event.payload.activated_at,
            },
            event_id=ids.generate(),
        )
        inngest_fixture.wait_for_database(
            lambda session: _profile_count(session, account_id) == 1
        )
        with inngest_fixture.inspection_session() as session:
            profile = session.get(GamificationProfileModel, account_id)
            assert profile is not None
            assert profile.total_xp == 0
            assert profile.level == 1

        inngest_fixture.publish(
            event.name,
            {
                'account_id': event.payload.account_id,
                'activated_at': event.payload.activated_at,
            },
            event_id=ids.generate(),
        )
        inngest_fixture.wait_for_database(
            lambda session: _profile_count(session, account_id) == 1
        )


def _profile_count(session: 'Session', account_id: str) -> int:
    return len(
        list(
            session.scalars(
                select(GamificationProfileModel).where(
                    GamificationProfileModel.account_id == account_id
                )
            )
        )
    )

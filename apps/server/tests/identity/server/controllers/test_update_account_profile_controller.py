from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from shifu.identity.pipes import IdentityPipe
from shifu.fakers.gamification.entities import GamificationProfileFaker
from shifu.gamification.core.domain.entities import PracticeDay
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from shifu.gamification.database.sqlalchemy.models import (
    PracticeDayModel,
    GamificationProfileModel,
)
from shifu.gamification.core.domain.structures import PracticeStreak
from tests.fixtures.account_security_fixture import AccountSecurityFixture


class TestUpdateAccountProfileController:
    @pytest.mark.parametrize('name', ['a', 'á' * 160])
    def test_should_save_normalized_profile_and_preserve_other_fields(
        self, account_security: AccountSecurityFixture, name: str
    ) -> None:
        fixture = account_security
        before = fixture.account
        response = fixture.client.patch(
            '/identity/accounts/me',
            headers=fixture.headers(),
            json={'display_name': '  ' + name + '  ', 'time_zone': 'Asia/Tokyo'},
        )
        assert response.status_code == 200, response.text
        assert response.json()['display_name'] == name
        assert response.json()['time_zone'] == 'Asia/Tokyo'
        with fixture.database.transaction() as repositories:
            actual = repositories.accounts.find_by_id(before.id)
            assert actual is not None
            assert actual.display_name == name
            assert actual.time_zone == 'Asia/Tokyo'
            assert actual.email == before.email
            assert actual.password_hash == before.password_hash
            assert actual.access_version == before.access_version
            assert actual.retained_session_id is None

    @pytest.mark.parametrize(
        ('payload', 'code', 'status'),
        [
            ({'display_name': '', 'time_zone': 'UTC'}, 'invalid_display_name', 400),
            ({'display_name': '  ', 'time_zone': 'UTC'}, 'invalid_display_name', 400),
            (
                {'display_name': 'a' * 161, 'time_zone': 'UTC'},
                'invalid_display_name',
                400,
            ),
            (
                {'display_name': 'Name', 'time_zone': 'bad/zone'},
                'invalid_time_zone',
                400,
            ),
            ({'display_name': 'Name', 'time_zone': None}, 'validation_error', 422),
            (
                {'display_name': 'Name', 'time_zone': 'UTC', 'account_id': 'other'},
                'validation_error',
                422,
            ),
        ],
    )
    def test_should_reject_invalid_input_without_mutation(
        self,
        account_security: AccountSecurityFixture,
        payload: dict[str, object],
        code: str,
        status: int,
    ) -> None:
        fixture = account_security
        response = fixture.client.patch(
            '/identity/accounts/me', headers=fixture.headers(), json=payload
        )
        assert response.status_code == status, response.text
        assert response.json()['code'] == code
        with fixture.database.transaction() as repositories:
            actual = repositories.accounts.find_by_id(fixture.account.id)
            assert actual is not None
            assert actual.display_name == fixture.account.display_name
            assert actual.time_zone == fixture.account.time_zone

    def test_should_preserve_recognized_history_for_both_owners(
        self, account_security: AccountSecurityFixture
    ) -> None:
        fixture = account_security
        database = SqlalchemyGamificationDatabase(fixture.engine)
        other = '00000000000000000000000099'
        now = datetime(2026, 1, 2, 1, 0, tzinfo=UTC)
        with database.transaction() as repositories:
            for index, account_id in enumerate((fixture.account.id, other)):
                repositories.profiles.add(
                    GamificationProfileFaker.fake(
                        account_id=account_id,
                        total_xp=450 + index * 100,
                        streak=PracticeStreak(
                            current=2, longest=3, latest_practice_date=date(2026, 1, 1)
                        ),
                        created_at=now,
                        updated_at=now,
                    )
                )
                repositories.practice_days.try_add(
                    PracticeDay.create(
                        id=str(index).zfill(26),
                        account_id=account_id,
                        time_zone='America/Sao_Paulo',
                        practiced_at=now,
                        recognized_at=now,
                    )
                )
        with fixture.engine.connect() as connection:
            profiles_before = connection.execute(
                select(GamificationProfileModel.__table__)
            ).all()
            history_before = connection.execute(
                select(PracticeDayModel.__table__)
            ).all()
        response = fixture.client.patch(
            '/identity/accounts/me',
            headers=fixture.headers(),
            json={'display_name': 'Updated', 'time_zone': 'Asia/Tokyo'},
        )
        assert response.status_code == 200, response.text
        with fixture.engine.connect() as connection:
            assert (
                connection.execute(select(PracticeDayModel.__table__)).all()
                == history_before
            )
        with fixture.engine.connect() as connection:
            assert (
                connection.execute(select(GamificationProfileModel.__table__)).all()
                == profiles_before
            )
        assert (
            fixture.client.get('/identity/session', headers=fixture.headers()).json()[
                'time_zone'
            ]
            == 'Asia/Tokyo'
        )

    def test_should_rollback_profile_when_composed_clock_fails(
        self, account_security: AccountSecurityFixture
    ) -> None:
        class UnavailableClock:
            def now(self) -> datetime:
                raise RuntimeError('private infrastructure detail')

        fixture = account_security
        fixture.app.dependency_overrides[IdentityPipe.get_clock_provider] = (
            UnavailableClock
        )
        response = fixture.client.patch(
            '/identity/accounts/me',
            headers=fixture.headers(),
            json={'display_name': 'Updated', 'time_zone': 'UTC'},
        )
        assert response.status_code == 503
        assert response.json()['code'] == 'service_unavailable'
        assert 'private infrastructure detail' not in response.text
        with fixture.database.transaction() as repositories:
            actual = repositories.accounts.find_by_id(fixture.account.id)
            assert actual is not None
            assert actual.display_name == fixture.account.display_name
            assert actual.time_zone == fixture.account.time_zone

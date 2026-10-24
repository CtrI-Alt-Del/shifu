from datetime import UTC, datetime

from shifu.fakers.gamification.entities import ActivityXpBalanceFaker
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from tests.fixtures.postgres_fixture import PostgresDatabase

ACCOUNT_ID = '01SHF00000000000000BALNCA'
OTHER_ACCOUNT_ID = '01SHF00000000000000BALNCB'
ACTIVITY_ID = '01SHF00000000000000ACTVTY'
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_finds_nothing_for_an_account_and_activity_without_a_balance(
    postgres_database: PostgresDatabase,
) -> None:
    database = SqlalchemyGamificationDatabase(postgres_database.engine)
    with database.transaction() as repositories:
        found = repositories.activity_xp_balances.find_by_account_id_and_activity_id(
            ACCOUNT_ID, ACTIVITY_ID
        )

    assert found is None


def test_adds_and_finds_the_balance_for_the_account_and_activity(
    postgres_database: PostgresDatabase,
) -> None:
    database = SqlalchemyGamificationDatabase(postgres_database.engine)
    balance = ActivityXpBalanceFaker.fake(
        account_id=ACCOUNT_ID,
        activity_id=ACTIVITY_ID,
        maximum_xp=10,
        granted_xp=4,
        updated_at=NOW,
    )

    with database.transaction() as repositories:
        repositories.activity_xp_balances.add(balance)

    with database.transaction() as repositories:
        found = repositories.activity_xp_balances.find_by_account_id_and_activity_id(
            ACCOUNT_ID, ACTIVITY_ID
        )

    assert found == balance


def test_updates_the_granted_xp_for_an_existing_balance(
    postgres_database: PostgresDatabase,
) -> None:
    database = SqlalchemyGamificationDatabase(postgres_database.engine)
    balance = ActivityXpBalanceFaker.fake(
        account_id=ACCOUNT_ID,
        activity_id=ACTIVITY_ID,
        maximum_xp=10,
        granted_xp=4,
        updated_at=NOW,
    )

    with database.transaction() as repositories:
        repositories.activity_xp_balances.add(balance)

    updated_balance = ActivityXpBalanceFaker.fake(
        id=balance.id,
        account_id=ACCOUNT_ID,
        activity_id=ACTIVITY_ID,
        maximum_xp=10,
        granted_xp=10,
        updated_at=NOW,
    )
    with database.transaction() as repositories:
        repositories.activity_xp_balances.update(updated_balance)

    with database.transaction() as repositories:
        found = repositories.activity_xp_balances.find_by_account_id_and_activity_id(
            ACCOUNT_ID, ACTIVITY_ID
        )

    assert found is not None
    assert found.granted_xp == 10


def test_removes_only_the_given_accounts_balances(
    postgres_database: PostgresDatabase,
) -> None:
    database = SqlalchemyGamificationDatabase(postgres_database.engine)
    with database.transaction() as repositories:
        repositories.activity_xp_balances.add(
            ActivityXpBalanceFaker.fake(
                account_id=ACCOUNT_ID, activity_id=ACTIVITY_ID, updated_at=NOW
            )
        )
        repositories.activity_xp_balances.add(
            ActivityXpBalanceFaker.fake(
                account_id=OTHER_ACCOUNT_ID, activity_id=ACTIVITY_ID, updated_at=NOW
            )
        )

    with database.transaction() as repositories:
        repositories.activity_xp_balances.remove_many_by_account_id(ACCOUNT_ID)

    with database.transaction() as repositories:
        assert (
            repositories.activity_xp_balances.find_by_account_id_and_activity_id(
                ACCOUNT_ID, ACTIVITY_ID
            )
            is None
        )
        assert (
            repositories.activity_xp_balances.find_by_account_id_and_activity_id(
                OTHER_ACCOUNT_ID, ACTIVITY_ID
            )
            is not None
        )

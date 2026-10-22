from datetime import UTC, datetime

from shifu.fakers.gamification.entities import GamificationProfileFaker, XpGrantFaker
from shifu.gamification.database.sqlalchemy import SqlalchemyGamificationDatabase
from tests.fixtures.postgres_fixture import PostgresDatabase

ACCOUNT_ID = '01SHF00000000000000PURGEA'
OTHER_ACCOUNT_ID = '01SHF00000000000000PURGEB'
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_removes_only_the_given_accounts_grants(
    postgres_database: PostgresDatabase,
) -> None:
    database = SqlalchemyGamificationDatabase(postgres_database.engine)
    with database.transaction() as repositories:
        repositories.profiles.add(
            GamificationProfileFaker.fake(
                account_id=ACCOUNT_ID, created_at=NOW, updated_at=NOW
            )
        )
        repositories.profiles.add(
            GamificationProfileFaker.fake(
                account_id=OTHER_ACCOUNT_ID, created_at=NOW, updated_at=NOW
            )
        )
        repositories.xp_grants.add(
            XpGrantFaker.fake(account_id=ACCOUNT_ID, occurred_at=NOW, granted_at=NOW)
        )
        repositories.xp_grants.add(
            XpGrantFaker.fake(
                account_id=OTHER_ACCOUNT_ID, occurred_at=NOW, granted_at=NOW
            )
        )

    with database.transaction() as repositories:
        repositories.xp_grants.remove_many_by_account_id(ACCOUNT_ID)

    with database.transaction() as repositories:
        assert repositories.xp_grants.find_many_by_account_id(ACCOUNT_ID) == ()
        assert (
            len(repositories.xp_grants.find_many_by_account_id(OTHER_ACCOUNT_ID)) == 1
        )

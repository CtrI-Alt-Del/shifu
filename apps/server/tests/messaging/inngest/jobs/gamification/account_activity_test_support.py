from datetime import UTC, datetime
from hashlib import sha256
from typing import TYPE_CHECKING

from shifu.identity.core.domain.enums import AccountDeletionReason, AccountStatus
from shifu.identity.database.sqlalchemy.models import AccountModel

if TYPE_CHECKING:
    from tests.fixtures.inngest_fixture import InngestFixture

_FIXTURE_PASSWORD_HASH = sha256(b'shifu-inngest-fixture').hexdigest()


def seed_active_account(fixture: 'InngestFixture', account_id: str) -> None:
    now = datetime.now(UTC)
    with fixture.inspection_session() as session:
        session.add(
            AccountModel(
                id=account_id,
                display_name='Active learner',
                email=f'{account_id}@example.test',
                password_hash=_FIXTURE_PASSWORD_HASH,
                status=AccountStatus.ACTIVE.value,
                access_version=1,
                created_at=now,
                updated_at=now,
                confirmed_at=now,
            )
        )
        session.commit()


def seed_deleted_account(fixture: 'InngestFixture', account_id: str) -> None:
    now = datetime.now(UTC)
    with fixture.inspection_session() as session:
        session.add(
            AccountModel(
                id=account_id,
                display_name='Closed learner',
                email=f'{account_id}@example.test',
                password_hash=_FIXTURE_PASSWORD_HASH,
                status=AccountStatus.DELETED.value,
                access_version=2,
                created_at=now,
                updated_at=now,
                deleted_at=now,
                deletion_reason=AccountDeletionReason.USER_REQUESTED.value,
            )
        )
        session.commit()

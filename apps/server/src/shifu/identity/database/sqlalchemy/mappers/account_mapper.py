from shifu.identity.core.domain.entities import Account
from shifu.identity.core.domain.enums import AccountDeletionReason, AccountStatus
from shifu.identity.database.sqlalchemy.models import AccountModel


class AccountMapper:
    @staticmethod
    def to_domain(model: AccountModel) -> Account:
        return Account(
            id=model.id,
            display_name=model.display_name,
            email=model.email,
            password_hash=model.password_hash,
            status=AccountStatus(model.status),
            access_version=model.access_version,
            time_zone=model.time_zone,
            created_at=model.created_at,
            updated_at=model.updated_at,
            confirmed_at=model.confirmed_at,
            deleted_at=model.deleted_at,
            deletion_reason=(
                AccountDeletionReason(model.deletion_reason)
                if model.deletion_reason is not None
                else None
            ),
        )

    @staticmethod
    def to_model(account: Account) -> AccountModel:
        return AccountModel(
            id=account.id,
            display_name=account.display_name,
            email=account.email,
            password_hash=account.password_hash,
            status=account.status.value,
            access_version=account.access_version,
            time_zone=account.time_zone,
            created_at=account.created_at,
            updated_at=account.updated_at,
            confirmed_at=account.confirmed_at,
            deleted_at=account.deleted_at,
            deletion_reason=(
                account.deletion_reason.value
                if account.deletion_reason is not None
                else None
            ),
        )

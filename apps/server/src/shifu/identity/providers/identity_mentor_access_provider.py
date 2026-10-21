from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.core.interfaces import IdentityDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import MentorAccessGrant, MentorUsage


class IdentityMentorAccessProvider:
    """Authorize Mentor operations against the current Identity account revision."""

    def __init__(self, database: IdentityDatabase) -> None:
        self._database = database

    def authorize(self, account_id: str, operation_key: str) -> MentorAccessGrant:
        revision = self._require_active(account_id)
        return MentorAccessGrant(
            account_id=account_id,
            access_revision=revision,
            operation_key=operation_key,
        )

    def assert_current(self, grant: MentorAccessGrant) -> None:
        revision = self._require_active(grant.account_id)
        if revision != grant.access_revision:
            raise AuthorizationError

    def record_usage(self, grant: MentorAccessGrant, usage: MentorUsage) -> None:
        self.assert_current(grant)
        if usage.operation_key != grant.operation_key:
            raise AuthorizationError

    def _require_active(self, account_id: str) -> str:
        with self._database.transaction() as repositories:
            account = repositories.accounts.find_by_id(account_id)
            if account is None or account.status is not AccountStatus.ACTIVE:
                raise AuthorizationError
            return str(account.access_version)

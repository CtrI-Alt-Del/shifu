from typing import Protocol

from shifu.shared.core.domain.structures import MentorAccessGrant, MentorUsage


class MentorAccessProvider(Protocol):
    def authorize(self, account_id: str, operation_key: str) -> MentorAccessGrant: ...

    def assert_current(self, grant: MentorAccessGrant) -> None: ...

    def record_usage(self, grant: MentorAccessGrant, usage: MentorUsage) -> None: ...

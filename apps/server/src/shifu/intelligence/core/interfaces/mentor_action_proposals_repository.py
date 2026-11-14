from typing import Protocol

from shifu.intelligence.core.domain.entities import MentorActionProposal


class MentorActionProposalsRepository(Protocol):
    def add(self, proposal: MentorActionProposal) -> None: ...

    def find_by_id_for_update(
        self, account_id: str, proposal_id: str
    ) -> MentorActionProposal | None: ...

    def find_many_by_session(
        self, account_id: str, session_id: str
    ) -> list[MentorActionProposal]:
        """The conversation's proposals, oldest first."""
        ...

    def exists_pending(self, account_id: str, session_id: str) -> bool: ...

    def update(self, proposal: MentorActionProposal) -> None: ...

    def remove_pending_by_attempt_id(self, account_id: str, attempt_id: str) -> int: ...

    def remove_by_session_id(self, account_id: str, session_id: str) -> int: ...

    def remove_by_account_id(self, account_id: str) -> int: ...

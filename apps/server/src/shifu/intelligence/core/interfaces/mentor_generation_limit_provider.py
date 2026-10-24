from typing import Protocol


class MentorGenerationLimitProvider(Protocol):
    def try_acquire(self, account_id: str, attempt_id: str) -> bool:
        """Take one slot for this attempt; True when it may call the model.

        Idempotent per attempt id. Raises ServiceUnavailableError when its store fails.
        """
        ...

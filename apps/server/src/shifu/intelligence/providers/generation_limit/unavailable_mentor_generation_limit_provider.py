class UnavailableMentorGenerationLimitProvider:
    """Deny every slot: general answers are off (no model or a limit of zero)."""

    def try_acquire(self, account_id: str, attempt_id: str) -> bool:
        del account_id, attempt_id
        return False

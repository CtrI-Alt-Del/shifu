from enum import StrEnum


class ResendConfirmationResultStatus(StrEnum):
    ACCEPTED = 'accepted'
    COOLDOWN = 'cooldown'

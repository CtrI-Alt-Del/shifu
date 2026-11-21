from enum import StrEnum


class PushDeliveryStatus(StrEnum):
    SENDING = 'sending'
    SENT = 'sent'
    FAILED = 'failed'

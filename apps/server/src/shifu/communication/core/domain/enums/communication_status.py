from enum import StrEnum


class CommunicationStatus(StrEnum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    SENT = 'sent'
    PERMANENTLY_FAILED = 'permanently-failed'
    REJECTED = 'rejected'

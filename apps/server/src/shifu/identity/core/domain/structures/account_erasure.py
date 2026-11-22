from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DeleteAccountInput:
    account_id: str
    erasure_id: UUID
    current_password: str
    confirmed: bool


@dataclass(frozen=True, slots=True)
class AccountErasureResult:
    state: Literal['closed']
    closed_at: datetime
    erasure: Literal['pending', 'completed']


@dataclass(frozen=True, slots=True)
class AccountErasureOverdueParticipant:
    erasure_id: UUID
    module: str
    closed_at: datetime
    due_at: datetime


@dataclass(frozen=True, slots=True)
class BrowserCapabilityStatus:
    state: Literal['active', 'revoked']

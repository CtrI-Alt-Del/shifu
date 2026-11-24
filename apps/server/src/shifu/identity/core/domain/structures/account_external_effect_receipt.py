from datetime import datetime
from typing import Literal
from uuid import UUID

from shifu.shared.core.domain.structures import structure

AccountExternalEffectReceiptState = Literal['in_flight', 'settled', 'unknown']


@structure
class AccountExternalEffectReceiptAdmission:
    account_id: str
    effect_id: UUID
    operation: str
    admitted_at: datetime
    state: AccountExternalEffectReceiptState
    is_new: bool


AccountExternalEffectReceiptResolution = Literal['applied', 'not_applied']


@structure
class AccountExternalEffectReceiptReconciliation:
    account_id: str
    effect_id: UUID
    operation: str
    resolution: AccountExternalEffectReceiptResolution
    operator_id: str
    evidence_reference: str
    evidence_sha256: str
    confirm_no_live_operation: bool

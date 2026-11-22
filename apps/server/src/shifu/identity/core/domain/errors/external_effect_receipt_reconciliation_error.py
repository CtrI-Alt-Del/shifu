from shifu.shared.core.domain.errors import ConflictError


class ExternalEffectReceiptReconciliationError(ConflictError):
    message: str = 'O receipt externo ou as evidências não permitem reconciliação.'
    title: str = 'Reconciliação bloqueada'

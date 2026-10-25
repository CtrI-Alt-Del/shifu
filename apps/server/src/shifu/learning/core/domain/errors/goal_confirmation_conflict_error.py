from shifu.shared.core.domain.errors import ConflictError


class GoalConfirmationConflictError(ConflictError):
    message = 'Esta confirmação já criou um objetivo com outro conteúdo.'

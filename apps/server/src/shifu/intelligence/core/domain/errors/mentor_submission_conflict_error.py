from shifu.shared.core.domain.errors import ConflictError


class MentorSubmissionConflictError(ConflictError):
    message: str = 'Esta chave de envio já foi usada para outra mensagem.'

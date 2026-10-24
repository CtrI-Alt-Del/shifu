from shifu.shared.core.domain.errors import ConflictError


class MentorActionConflictError(ConflictError):
    message: str = 'Esta confirmação já foi usada com outros dados.'
    title: str = 'Confirmação em conflito'

from shifu.shared.core.domain.errors import NotFoundError


class MentorSessionNotFoundError(NotFoundError):
    message: str = 'Conversa do Mentor não encontrada.'

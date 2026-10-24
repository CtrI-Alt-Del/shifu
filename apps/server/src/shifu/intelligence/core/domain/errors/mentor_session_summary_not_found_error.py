from shifu.shared.core.domain.errors import NotFoundError


class MentorSessionSummaryNotFoundError(NotFoundError):
    message: str = 'Resumo da conversa não encontrado.'

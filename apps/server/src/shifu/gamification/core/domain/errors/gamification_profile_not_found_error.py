from shifu.shared.core.domain.errors import NotFoundError


class GamificationProfileNotFoundError(NotFoundError):
    title: str = 'Perfil de gamificação não encontrado'
    message: str = 'Este perfil de gamificação não está disponível.'

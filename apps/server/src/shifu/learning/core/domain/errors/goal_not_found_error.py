from shifu.shared.core.domain.errors import NotFoundError


class GoalNotFoundError(NotFoundError):
    message: str = 'O objetivo de aprendizagem não foi encontrado.'

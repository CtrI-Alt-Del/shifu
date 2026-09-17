from shifu.shared.core.domain.errors import ConflictError


class EmailAlreadyInUseError(ConflictError):
    message: str = 'Não foi possível cadastrar a conta com o e-mail informado.'

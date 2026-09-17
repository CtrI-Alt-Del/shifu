from shifu.shared.core.domain.errors import ServiceUnavailableError


class EmailDeliveryUnavailableError(ServiceUnavailableError):
    message: str = (
        'Não foi possível enviar o e-mail no momento. Tente novamente mais tarde.'
    )

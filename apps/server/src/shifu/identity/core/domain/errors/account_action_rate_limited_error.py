from shifu.shared.core.domain.errors import RateLimitError


class AccountActionRateLimitedError(RateLimitError):
    message: str = 'Aguarde antes de solicitar um novo link.'

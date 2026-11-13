from shifu.shared.core.domain.errors import RateLimitError


class AiQuotaExhaustedError(RateLimitError):
    title: str = 'Cota de IA esgotada'
    message: str = (
        'Sua cota mensal de IA acabou. '
        'O Mentor e o planejamento assistido voltam na renovação.'
    )

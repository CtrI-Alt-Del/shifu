from shifu.shared.core.domain.errors import ValidationError


class InvalidEvaluationRuleError(ValidationError):
    message: str = 'A regra de avaliação é inválida.'

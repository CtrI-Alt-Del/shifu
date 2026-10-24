from shifu.shared.core.domain.errors import ValidationError


class PlanningAnswersInvalidError(ValidationError):
    message: str = 'Responda todas as perguntas do lote com alternativas válidas.'

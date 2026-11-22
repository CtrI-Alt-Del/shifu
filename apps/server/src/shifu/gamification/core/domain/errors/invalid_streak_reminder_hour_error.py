from shifu.gamification.core.domain.errors.invalid_gamification_error import (
    InvalidGamificationError,
)


class InvalidStreakReminderHourError(InvalidGamificationError):
    title: str = 'Hora de lembrete inválida'
    message: str = 'Escolha uma hora cheia entre 06:00 e 22:00.'

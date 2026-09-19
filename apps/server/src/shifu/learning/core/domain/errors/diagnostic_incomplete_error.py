from shifu.shared.core.domain.errors import ConflictError


class DiagnosticIncompleteError(ConflictError):
    message: str = 'O diagnóstico ainda não foi concluído.'

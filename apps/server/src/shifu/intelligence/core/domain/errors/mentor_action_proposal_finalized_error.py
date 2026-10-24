from shifu.shared.core.domain.errors import ConflictError


class MentorActionProposalFinalizedError(ConflictError):
    message: str = 'Esta ação já foi concluída.'
    title: str = 'Ação já concluída'

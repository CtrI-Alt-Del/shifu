from shifu.shared.core.domain.structures import structure

UNKNOWN_OPTION_ID = 'nao-sei'
UNKNOWN_OPTION_TEXT = 'Não sei'
OTHER_OPTION_ID = 'outro'
OTHER_OPTION_TEXT = 'Outro'
OTHER_TEXT_MAX_LENGTH = 200


@structure
class PlanningOption:
    id: str
    text: str
    exclusive: bool = False
    # An open option is answered with the learner's own text.
    open: bool = False

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.text.strip():
            raise ValueError('An option needs an identifier and a text.')
        if self.exclusive and self.open:
            raise ValueError('An option cannot be both exclusive and open.')

    @staticmethod
    def unknown() -> 'PlanningOption':
        return PlanningOption(
            id=UNKNOWN_OPTION_ID, text=UNKNOWN_OPTION_TEXT, exclusive=True
        )

    @staticmethod
    def other() -> 'PlanningOption':
        return PlanningOption(id=OTHER_OPTION_ID, text=OTHER_OPTION_TEXT, open=True)

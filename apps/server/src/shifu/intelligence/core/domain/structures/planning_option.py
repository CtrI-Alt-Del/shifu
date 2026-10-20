from shifu.shared.core.domain.structures import structure

UNKNOWN_OPTION_ID = 'nao-sei'
UNKNOWN_OPTION_TEXT = 'Não sei'


@structure
class PlanningOption:
    id: str
    text: str
    exclusive: bool = False

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.text.strip():
            raise ValueError('An option needs an identifier and a text.')

    @staticmethod
    def unknown() -> 'PlanningOption':
        return PlanningOption(
            id=UNKNOWN_OPTION_ID, text=UNKNOWN_OPTION_TEXT, exclusive=True
        )

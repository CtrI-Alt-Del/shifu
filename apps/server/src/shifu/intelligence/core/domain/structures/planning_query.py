from shifu.shared.core.domain.structures import structure


@structure
class PlanningQuery:
    intent: str
    answers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.intent.strip():
            raise ValueError('A planning intent cannot be blank.')
        if any(not answer.strip() for answer in self.answers):
            raise ValueError('A planning answer cannot be blank.')

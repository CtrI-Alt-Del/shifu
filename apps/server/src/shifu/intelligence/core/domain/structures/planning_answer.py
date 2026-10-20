from shifu.shared.core.domain.structures import structure


@structure
class PlanningAnswer:
    question_id: str
    option_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.question_id.strip():
            raise ValueError('An answer needs a question identifier.')
        if any(not option_id.strip() for option_id in self.option_ids):
            raise ValueError('Option identifiers cannot be blank.')

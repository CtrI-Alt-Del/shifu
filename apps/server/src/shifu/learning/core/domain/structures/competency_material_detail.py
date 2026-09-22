from shifu.shared.core.domain.structures import structure


@structure
class CompetencyMaterialDetail:
    id: str
    title: str
    position: int

    def __post_init__(self) -> None:
        if self.position < 1:
            raise ValueError('Competency content positions must be positive.')

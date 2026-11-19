from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class FillBlanksConceptCriterion:
    concept_id: str
    criterion: str
    examples: str
    limits: str
    blank_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ('concept_id', 'criterion', 'examples', 'limits'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=InvalidActivityError
                ).value,
            )
        keys = tuple(
            NonEmptyText.create(key, error_type=InvalidActivityError).value
            for key in self.blank_keys
        )
        if not keys or len(keys) != len(set(keys)):
            raise InvalidActivityError

        object.__setattr__(self, 'blank_keys', keys)

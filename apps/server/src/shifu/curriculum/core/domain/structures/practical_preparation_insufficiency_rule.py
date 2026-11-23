from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class PracticeInsufficiencyRule:
    record_key: str
    criterion_keys: tuple[str, ...]
    comment: str

    def __post_init__(self) -> None:
        for name in ('record_key', 'comment'):
            object.__setattr__(
                self,
                name,
                NonEmptyText.create(
                    getattr(self, name), error_type=InvalidActivityError
                ).value,
            )
        for key in self.criterion_keys:
            NonEmptyText.create(key, error_type=InvalidActivityError)
        if not self.criterion_keys or len(self.criterion_keys) != len(
            set(self.criterion_keys)
        ):
            raise InvalidActivityError

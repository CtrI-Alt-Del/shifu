from typing import Literal

from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.shared.core.domain.structures import NonEmptyText, structure

from .code_concept_criterion import CodeConceptCriterion


@structure
class TranslationQuestion:
    key: str
    prompt: str
    source_language: str
    target_language: str
    source_text: str
    reference_translations: tuple[str, ...]
    concept_criteria: tuple[CodeConceptCriterion, ...] = ()
    kind: Literal['translation'] = 'translation'

    def __post_init__(self) -> None:
        for value in (
            self.key,
            self.prompt,
            self.source_language,
            self.target_language,
            self.source_text,
        ):
            NonEmptyText.create(value, error_type=InvalidActivityError)
        for translation in self.reference_translations:
            NonEmptyText.create(translation, error_type=InvalidActivityError)
        if (
            not self.reference_translations
            or len(self.reference_translations) != len(set(self.reference_translations))
            or self.kind != 'translation'
            or len(self.concept_criteria)
            != len({item.concept_id for item in self.concept_criteria})
        ):
            raise InvalidActivityError

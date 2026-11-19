from shifu.shared.core.domain.structures import structure


@structure
class TranslationQuestionCriterionDetail:
    key: str
    name: str
    weight_percentage: int


@structure
class TranslationQuestionDetail:
    key: str
    kind: str
    prompt: str
    source_language: str
    target_language: str
    source_text: str
    criteria: tuple[TranslationQuestionCriterionDetail, ...]

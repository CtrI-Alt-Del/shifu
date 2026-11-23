from shifu.shared.core.domain.structures import (
    CurriculumChoiceQuestionSnapshot,
    CurriculumFillBlanksQuestionSnapshot,
    CurriculumHtmlCssJsQuestionSnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumPairMatchingQuestionSnapshot,
    CurriculumOrderingQuestionSnapshot,
    CurriculumPracticalPreparationQuestionSnapshot,
    CurriculumReactFastifyQuestionSnapshot,
    CurriculumReactQuestionSnapshot,
    CurriculumTranslationQuestionSnapshot,
)

type QuestionSnapshots = tuple[object, ...]

type LearningQuestionSnapshot = (
    CurriculumChoiceQuestionSnapshot
    | CurriculumJavascriptStdinQuestionSnapshot
    | CurriculumReactQuestionSnapshot
    | CurriculumHtmlCssJsQuestionSnapshot
    | CurriculumReactFastifyQuestionSnapshot
    | CurriculumOrderingQuestionSnapshot
    | CurriculumFillBlanksQuestionSnapshot
    | CurriculumTranslationQuestionSnapshot
    | CurriculumPairMatchingQuestionSnapshot
    | CurriculumPracticalPreparationQuestionSnapshot
)


class MixedQuestionSnapshots:
    CODE = (
        CurriculumJavascriptStdinQuestionSnapshot,
        CurriculumReactQuestionSnapshot,
        CurriculumHtmlCssJsQuestionSnapshot,
        CurriculumReactFastifyQuestionSnapshot,
    )
    NON_CHOICE = (
        *CODE,
        CurriculumFillBlanksQuestionSnapshot,
        CurriculumTranslationQuestionSnapshot,
        CurriculumPairMatchingQuestionSnapshot,
        CurriculumOrderingQuestionSnapshot,
        CurriculumPracticalPreparationQuestionSnapshot,
    )

    @staticmethod
    def has_non_choice(questions: QuestionSnapshots) -> bool:
        """A Learning Activity needs the mixed snapshot unless it is choice-only."""
        return any(
            isinstance(question, MixedQuestionSnapshots.NON_CHOICE)
            for question in questions
        )

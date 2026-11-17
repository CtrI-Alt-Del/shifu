from shifu.shared.core.domain.structures import (
    CurriculumFillBlanksQuestionSnapshot,
    CurriculumHtmlCssJsQuestionSnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumReactFastifyQuestionSnapshot,
    CurriculumReactQuestionSnapshot,
)

type QuestionSnapshots = tuple[object, ...]


class MixedQuestionSnapshots:
    CODE = (
        CurriculumJavascriptStdinQuestionSnapshot,
        CurriculumReactQuestionSnapshot,
        CurriculumHtmlCssJsQuestionSnapshot,
        CurriculumReactFastifyQuestionSnapshot,
    )
    NON_CHOICE = (*CODE, CurriculumFillBlanksQuestionSnapshot)

    @staticmethod
    def has_non_choice(questions: QuestionSnapshots) -> bool:
        """A Learning Activity needs the mixed snapshot unless it is choice-only."""
        return any(
            isinstance(question, MixedQuestionSnapshots.NON_CHOICE)
            for question in questions
        )

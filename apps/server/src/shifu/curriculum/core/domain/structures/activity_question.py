from .code_question import CodeQuestion
from .javascript_stdin_question import JavascriptStdinQuestion
from .multiple_selection_question import MultipleSelectionQuestion
from .single_choice_question import SingleChoiceQuestion


type ActivityQuestion = (
    SingleChoiceQuestion
    | MultipleSelectionQuestion
    | CodeQuestion
    | JavascriptStdinQuestion
)

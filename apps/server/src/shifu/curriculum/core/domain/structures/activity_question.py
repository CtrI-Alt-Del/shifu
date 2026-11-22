from .code_question import CodeQuestion
from .fill_blanks_question import FillBlanksQuestion
from .html_css_js_question import HtmlCssJsQuestion
from .javascript_stdin_question import JavascriptStdinQuestion
from .multiple_selection_question import MultipleSelectionQuestion
from .ordering_question import OrderingQuestion
from .pair_matching_question import PairMatchingQuestion
from .practical_preparation_question import PracticalPreparationQuestion
from .react_question import ReactQuestion
from .react_fastify_question import ReactFastifyQuestion
from .single_choice_question import SingleChoiceQuestion
from .translation_question import TranslationQuestion


type ActivityQuestion = (
    SingleChoiceQuestion
    | MultipleSelectionQuestion
    | CodeQuestion
    | JavascriptStdinQuestion
    | ReactQuestion
    | HtmlCssJsQuestion
    | ReactFastifyQuestion
    | OrderingQuestion
    | FillBlanksQuestion
    | TranslationQuestion
    | PairMatchingQuestion
    | PracticalPreparationQuestion
)

from .code_question import CodeQuestion
from .html_css_js_question import HtmlCssJsQuestion
from .javascript_stdin_question import JavascriptStdinQuestion
from .multiple_selection_question import MultipleSelectionQuestion
from .react_question import ReactQuestion
from .single_choice_question import SingleChoiceQuestion


type ActivityQuestion = (
    SingleChoiceQuestion
    | MultipleSelectionQuestion
    | CodeQuestion
    | JavascriptStdinQuestion
    | ReactQuestion
    | HtmlCssJsQuestion
)

from shifu.learning.core.domain.structures.code_answer import CodeAnswer
from shifu.learning.core.domain.structures.multiple_selection_answer import (
    MultipleSelectionAnswer,
)
from shifu.learning.core.domain.structures.single_choice_answer import (
    SingleChoiceAnswer,
)
from shifu.learning.core.domain.structures.ordering_answer import OrderingAnswer
from shifu.learning.core.domain.structures.translation_answer import TranslationAnswer

type ActivityAnswer = (
    SingleChoiceAnswer
    | MultipleSelectionAnswer
    | CodeAnswer
    | OrderingAnswer
    | TranslationAnswer
)

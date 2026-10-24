from typing import ClassVar

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    ChoiceOption,
    CodeInconclusiveComment,
    CodeRubricComment,
    CodeRubricCriterion,
    CodeRubricEvaluationPart,
    CorrectnessEvaluationPart,
    EvaluationRule,
    HtmlCssJsDependency,
    HtmlCssJsInitialFile,
    HtmlCssJsPermittedCommand,
    HtmlCssJsQuestion,
    SingleChoiceQuestion,
)
from shifu.shared.database.seed_data import (
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_GOAL_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
)


class HtmlCssJsControllerFixture:
    ACTIVITY_ID: ClassVar[str] = '01SHF000000000000000000092'
    PROMPT: ClassVar[str] = 'Crie uma página de curso responsiva'
    INITIAL_HTML: ClassVar[str] = '<main><h1>Curso</h1></main>'
    INITIAL_CSS: ClassVar[str] = 'main { max-width: 60rem; }'
    INITIAL_JS: ClassVar[str] = 'const title = "Curso";'
    READ_ONLY_MANIFEST: ClassVar[str] = '{"scripts":{"dev":"vite"}}'
    SUBMITTED_HTML: ClassVar[str] = '<main><h1>Meu curso</h1></main>'
    SUBMITTED_CSS: ClassVar[str] = 'main { color: rebeccapurple; }'
    SUBMITTED_JS: ClassVar[str] = 'document.title = "Meu curso";'

    @staticmethod
    def activity() -> Activity:
        choices = tuple(
            SingleChoiceQuestion(
                key=f'q{index}',
                prompt='Escolha',
                options=(
                    ChoiceOption(key='a', text='A', is_correct=True),
                    ChoiceOption(key='b', text='B', is_correct=False),
                ),
                correct_explanation='Certo',
                incorrect_explanation='Errado',
            )
            for index in (1, 2)
        )
        question = HtmlCssJsQuestion(
            key='q3',
            prompt=HtmlCssJsControllerFixture.PROMPT,
            initial_files=(
                HtmlCssJsInitialFile(
                    path='index.html',
                    content=HtmlCssJsControllerFixture.INITIAL_HTML,
                    editable=True,
                ),
                HtmlCssJsInitialFile(
                    path='styles.css',
                    content=HtmlCssJsControllerFixture.INITIAL_CSS,
                    editable=True,
                ),
                HtmlCssJsInitialFile(
                    path='script.js',
                    content=HtmlCssJsControllerFixture.INITIAL_JS,
                    editable=True,
                ),
                HtmlCssJsInitialFile(
                    path='package.json',
                    content=HtmlCssJsControllerFixture.READ_ONLY_MANIFEST,
                    editable=False,
                ),
            ),
            entrypoint='index.html',
            fixed_dependencies=(HtmlCssJsDependency(name='vite', version='7.0.0'),),
            permitted_commands=(
                HtmlCssJsPermittedCommand(
                    id='dev', executable='npm', arguments=('run', 'dev')
                ),
            ),
            concept_criteria=(),
        )
        criterion = CodeRubricCriterion(
            key='quality',
            name='Qualidade visual',
            description='Apresenta a informação de forma clara e responsiva',
            weight_percentage=100,
            required=True,
            fixed_comments=tuple(
                CodeRubricComment(
                    id=f'comment-{level}', level=level, text=f'Private comment {level}'
                )
                for level in (0, 25, 50, 75, 100)
            ),
            inconclusive_comment=CodeInconclusiveComment(
                id='unknown', text='Private inconclusive comment'
            ),
        )
        return Activity.create(
            id=HtmlCssJsControllerFixture.ACTIVITY_ID,
            competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='Atividade HTML',
            objective='Praticar HTML, CSS e JavaScript',
            questions=(*choices, question),
            evaluation_rule=EvaluationRule(
                parts=(
                    CorrectnessEvaluationPart(question_key='q1', weight_percentage=30),
                    CorrectnessEvaluationPart(question_key='q2', weight_percentage=30),
                    CodeRubricEvaluationPart(
                        question_key='q3', weight_percentage=40, criteria=(criterion,)
                    ),
                )
            ),
        )

    @staticmethod
    def activity_path() -> str:
        return (
            f'/learning/goals/{SEED_ADAPTIVE_LAB_GOAL_ID}'
            f'/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}'
            f'/competencies/{SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID}'
            f'/activities/{HtmlCssJsControllerFixture.ACTIVITY_ID}'
        )

    @staticmethod
    def answer_files() -> list[dict[str, str]]:
        return [
            {
                'path': 'index.html',
                'content': HtmlCssJsControllerFixture.SUBMITTED_HTML,
            },
            {
                'path': 'styles.css',
                'content': HtmlCssJsControllerFixture.SUBMITTED_CSS,
            },
            {
                'path': 'script.js',
                'content': HtmlCssJsControllerFixture.SUBMITTED_JS,
            },
        ]

    @staticmethod
    def composed_files() -> list[dict[str, str]]:
        return [
            {
                'path': 'index.html',
                'content': HtmlCssJsControllerFixture.SUBMITTED_HTML,
            },
            {
                'path': 'package.json',
                'content': HtmlCssJsControllerFixture.READ_ONLY_MANIFEST,
            },
            {
                'path': 'script.js',
                'content': HtmlCssJsControllerFixture.SUBMITTED_JS,
            },
            {
                'path': 'styles.css',
                'content': HtmlCssJsControllerFixture.SUBMITTED_CSS,
            },
        ]

    @staticmethod
    def submission(revision: str) -> dict[str, object]:
        return {
            'submission_key': 'e9aa7b85-c95b-4319-b98e-5ca293c09f62',
            'activity_revision': revision,
            'answers': [
                {
                    'kind': 'single_choice',
                    'question_key': key,
                    'selected_option_keys': ['a'],
                }
                for key in ('q1', 'q2')
            ]
            + [
                {
                    'kind': 'html_css_js',
                    'question_key': 'q3',
                    'files': HtmlCssJsControllerFixture.answer_files(),
                }
            ],
        }

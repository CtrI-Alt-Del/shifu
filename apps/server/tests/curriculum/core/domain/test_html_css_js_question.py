from dataclasses import FrozenInstanceError
import pytest

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.curriculum.core.domain.structures import (
    CodeInconclusiveComment,
    CodeRubricComment,
    CodeRubricCriterion,
    CodeRubricEvaluationPart,
    CorrectnessEvaluationPart,
    HtmlCssJsDependency,
    HtmlCssJsInitialFile,
    HtmlCssJsPermittedCommand,
    HtmlCssJsQuestion,
    EvaluationRule,
)
from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import (
    CurriculumCodeConceptCriterionSnapshot,
    CurriculumCodeInconclusiveObservationSnapshot,
    CurriculumCodeLevelObservationSnapshot,
    CurriculumHtmlCssJsDependencySnapshot,
    CurriculumHtmlCssJsInitialFileSnapshot,
    CurriculumHtmlCssJsPermittedCommandSnapshot,
    CurriculumHtmlCssJsQuestionSnapshot,
)
from shifu.shared.database.sqlalchemy.serialization import Serialization


def _question(
    *,
    initial_files: tuple[HtmlCssJsInitialFile, ...] | None = None,
    entrypoint: str = 'index.html',
) -> HtmlCssJsQuestion:
    return HtmlCssJsQuestion(
        key='html-1',
        prompt='Build a page',
        initial_files=(
            initial_files
            if initial_files is not None
            else (
                HtmlCssJsInitialFile(
                    path='index.html', content='<main></main>', editable=True
                ),
                HtmlCssJsInitialFile(path='styles.css', content='', editable=True),
                HtmlCssJsInitialFile(path='script.js', content='', editable=True),
                HtmlCssJsInitialFile(path='package.json', content='{}', editable=False),
            )
        ),
        entrypoint=entrypoint,
        fixed_dependencies=(HtmlCssJsDependency(name='vite', version='7.0.0'),),
        permitted_commands=(
            HtmlCssJsPermittedCommand(
                id='dev', executable='npm', arguments=('run', 'dev')
            ),
        ),
        concept_criteria=(),
    )


def _rubric(question_key: str) -> CodeRubricEvaluationPart:
    criterion = CodeRubricCriterion(
        key='quality',
        name='Quality',
        description='Uses semantic HTML and responsive CSS',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CodeRubricComment(id=f'quality-{level}', level=level, text=f'Level {level}')
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CodeInconclusiveComment(
            id='quality-inconclusive', text='Insufficient evidence'
        ),
    )
    return CodeRubricEvaluationPart(
        question_key=question_key,
        weight_percentage=100,
        criteria=(criterion,),
    )


class TestHtmlCssJsQuestion:
    def test_should_create_immutable_question_with_exact_project_contract(self) -> None:
        question = _question()

        assert question.kind == 'html_css_js'
        assert question.entrypoint == 'index.html'
        assert tuple(item.path for item in question.initial_files) == (
            'index.html',
            'styles.css',
            'script.js',
            'package.json',
        )
        with pytest.raises(FrozenInstanceError):
            question.prompt = 'changed'  # type: ignore[misc]

    @pytest.mark.parametrize(
        'path',
        (
            '/index.html',
            '../index.html',
            'src/../index.html',
            'src\\index.html',
            'src//index.html',
            '.hidden.html',
            f'{"a" * 65}.html',
            f'{"a" * 237}.html',
        ),
    )
    def test_should_reject_unsafe_initial_paths(self, path: str) -> None:
        with pytest.raises(InvalidActivityError):
            HtmlCssJsInitialFile(path=path, content='', editable=True)

    @pytest.mark.parametrize(
        'path',
        (
            'package.json',
            'src/vite.config.js',
            'tsconfig.json',
            'src/site.config.html',
            '.git/index.html',
            'node_modules/evil.js',
        ),
    )
    def test_should_reject_editable_configuration_and_runtime_paths(
        self, path: str
    ) -> None:
        with pytest.raises(InvalidActivityError):
            HtmlCssJsInitialFile(path=path, content='', editable=True)

    def test_should_require_html_entrypoint_and_collision_free_unique_files(
        self,
    ) -> None:
        with pytest.raises(InvalidActivityError):
            _question(entrypoint='styles.css')
        with pytest.raises(InvalidActivityError):
            _question(
                initial_files=(
                    HtmlCssJsInitialFile(path='index.html', content='', editable=True),
                    HtmlCssJsInitialFile(path='index.html', content='', editable=True),
                )
            )
        with pytest.raises(InvalidActivityError):
            _question(
                initial_files=(
                    HtmlCssJsInitialFile(path='src', content='', editable=False),
                    HtmlCssJsInitialFile(
                        path='src/index.html', content='', editable=True
                    ),
                ),
                entrypoint='src/index.html',
            )

    def test_should_require_code_rubric_and_reject_html_diagnostics(self) -> None:
        question = _question()
        with pytest.raises(InvalidActivityError):
            Activity(
                id='activity-1',
                competency_id='competency-1',
                activity_type=ActivityType.LEARNING,
                difficulty=ActivityDifficulty.EASY,
                title='HTML activity',
                objective='Build a page',
                questions=(question,),
                evaluation_rule=EvaluationRule(
                    parts=(
                        CorrectnessEvaluationPart(
                            question_key=question.key, weight_percentage=100
                        ),
                    )
                ),
            )

        activity = Activity(
            id='activity-1',
            competency_id='competency-1',
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='HTML activity',
            objective='Build a page',
            questions=(question,),
            evaluation_rule=EvaluationRule(parts=(_rubric(question.key),)),
        )
        assert activity.questions == (question,)

        with pytest.raises(InvalidActivityError):
            Activity(
                id='activity-1',
                competency_id='competency-1',
                activity_type=ActivityType.DIAGNOSTIC,
                difficulty=ActivityDifficulty.EASY,
                title='HTML diagnostic',
                objective='Build a page',
                questions=(question,),
                evaluation_rule=EvaluationRule(parts=(_rubric(question.key),)),
            )


def _snapshot() -> CurriculumHtmlCssJsQuestionSnapshot:
    return CurriculumHtmlCssJsQuestionSnapshot(
        key='html-1',
        prompt='Build a page',
        initial_files=(
            CurriculumHtmlCssJsInitialFileSnapshot(
                path='index.html', content='<main></main>', editable=True
            ),
            CurriculumHtmlCssJsInitialFileSnapshot(
                path='package.json', content='{}', editable=False
            ),
        ),
        entrypoint='index.html',
        fixed_dependencies=(
            CurriculumHtmlCssJsDependencySnapshot(name='vite', version='7.0.0'),
        ),
        permitted_commands=(
            CurriculumHtmlCssJsPermittedCommandSnapshot(
                id='dev', executable='npm', arguments=('run', 'dev')
            ),
        ),
        concept_criteria=(
            CurriculumCodeConceptCriterionSnapshot(
                concept_id='concept-1',
                description='Uses semantic tags',
                level_observations=tuple(
                    CurriculumCodeLevelObservationSnapshot(
                        id=f'observation-{level}',
                        level=level,
                        evidence='Semantic elements are present',
                        interpretation_limit='Only inspect the submitted page',
                    )
                    for level in (0, 25, 50, 75, 100)
                ),
                inconclusive_observation=CurriculumCodeInconclusiveObservationSnapshot(
                    id='observation-unknown', text='Could not determine'
                ),
            ),
        ),
    )


class TestCurriculumHtmlCssJsQuestionSnapshot:
    def test_should_round_trip_snapshot_and_reject_invalid_projects(self) -> None:
        question = _snapshot()
        restored = Serialization.deserialize_value(
            Serialization.serialize_value(question),
            CurriculumHtmlCssJsQuestionSnapshot,
        )

        assert restored == question
        with pytest.raises(ValidationError):
            CurriculumHtmlCssJsInitialFileSnapshot(
                path='../index.html', content='', editable=True
            )
        with pytest.raises(ValidationError):
            CurriculumHtmlCssJsInitialFileSnapshot(
                path='package.json', content='{}', editable=True
            )

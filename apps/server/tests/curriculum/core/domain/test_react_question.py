from dataclasses import FrozenInstanceError

import pytest

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.errors import (
    InvalidActivityError,
    InvalidEvaluationRuleError,
)
from shifu.curriculum.core.domain.structures import (
    CodeInconclusiveComment,
    CodeRubricComment,
    CodeRubricCriterion,
    CodeRubricEvaluationPart,
    CorrectnessEvaluationPart,
    EvaluationRule,
    ReactAdditionalFilePolicy,
    ReactDependency,
    ReactInitialFile,
    ReactPermittedCommand,
    ReactQuestion,
)
from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import (
    CurriculumReactAdditionalFilePolicySnapshot,
    CurriculumReactDependencySnapshot,
    CurriculumReactInitialFileSnapshot,
    CurriculumReactPermittedCommandSnapshot,
    CurriculumReactQuestionSnapshot,
)
from shifu.shared.database.sqlalchemy.serialization import Serialization


def _policy(
    *,
    directories: tuple[str, ...] = ('src/components',),
    extensions: tuple[str, ...] = ('.tsx', '.css'),
    max_files: int = 3,
) -> ReactAdditionalFilePolicy:
    return ReactAdditionalFilePolicy(
        allowed_directories=directories,
        allowed_extensions=extensions,
        max_files=max_files,
    )


def _question(
    *,
    policy: ReactAdditionalFilePolicy | None = None,
    initial_files: tuple[ReactInitialFile, ...] | None = None,
) -> ReactQuestion:
    return ReactQuestion(
        key='react-1',
        prompt='Build a component',
        initial_files=initial_files
        if initial_files is not None
        else (
            ReactInitialFile(path='package.json', content='{}', editable=False),
            ReactInitialFile(path='src/App.tsx', content='', editable=True),
        ),
        entrypoint='src/App.tsx',
        fixed_dependencies=(ReactDependency(name='react', version='19.0.0'),),
        permitted_commands=(
            ReactPermittedCommand(id='dev', executable='npm', arguments=('run', 'dev')),
        ),
        concept_criteria=(),
        additional_file_policy=policy,
    )


def _rubric_part(question_key: str) -> CodeRubricEvaluationPart:
    criterion = CodeRubricCriterion(
        key='quality',
        name='Quality',
        description='Uses the requested component structure',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CodeRubricComment(id=f'quality-{level}', level=level, text=f'Level {level}')
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CodeInconclusiveComment(
            id='quality-unknown', text='Insufficient evidence'
        ),
    )
    return CodeRubricEvaluationPart(
        question_key=question_key,
        weight_percentage=100,
        criteria=(criterion,),
    )


def _activity(
    question: ReactQuestion,
    part: CodeRubricEvaluationPart | None,
    activity_type: ActivityType = ActivityType.LEARNING,
) -> Activity:
    return Activity(
        id='activity-1',
        competency_id='competency-1',
        activity_type=activity_type,
        difficulty=ActivityDifficulty.EASY,
        title='React activity',
        objective='Build a component',
        questions=(question,),
        evaluation_rule=EvaluationRule(parts=(part,) if part is not None else ()),
    )


def test_should_accept_curricular_policy_paths_by_segment() -> None:
    policy = _policy()

    assert policy.allows('src/components/Button.tsx')
    assert policy.allows('src/components/forms/Field.tsx')
    assert not policy.allows('src/components-old/Button.tsx')
    assert not policy.allows('src/App.tsx')
    assert not policy.allows('src/components/Button.js')


@pytest.mark.parametrize(
    'path',
    (
        '/src/components/Button.tsx',
        '../Button.tsx',
        'src/../components/Button.tsx',
        'src\\components\\Button.tsx',
        'src//components/Button.tsx',
        'src/components/.hidden.tsx',
        'src/components/éxito.tsx',
        f'src/components/{"a" * 65}.tsx',
        f'src/{"a" * 235}.tsx',
        'src/components/package.json',
        'src/components/tsconfig.json',
        'src/components/tsconfig.app.json',
        'src/components/vite.config.tsx',
    ),
)
def test_should_reject_noncanonical_or_configuration_additional_paths(
    path: str,
) -> None:
    assert not _policy(extensions=('.tsx', '.json')).allows(path)


def test_should_reject_invalid_policy_values() -> None:
    with pytest.raises(InvalidActivityError):
        _policy(directories=('src/../components',))
    with pytest.raises(InvalidActivityError):
        _policy(extensions=('.exe',))
    with pytest.raises(InvalidActivityError):
        _policy(max_files=0)
    with pytest.raises(InvalidActivityError):
        _policy(max_files=33)
    with pytest.raises(InvalidActivityError):
        _policy(max_files=True)  # type: ignore[arg-type]


def test_should_require_editable_react_entrypoint_and_collision_free_files() -> None:
    with pytest.raises(InvalidActivityError):
        _question(
            initial_files=(
                ReactInitialFile(path='package.json', content='{}', editable=False),
            )
        )
    with pytest.raises(InvalidActivityError):
        _question(
            initial_files=(
                ReactInitialFile(path='src', content='', editable=False),
                ReactInitialFile(path='src/App.tsx', content='', editable=True),
            )
        )
    with pytest.raises(InvalidActivityError):
        _question(
            initial_files=(
                ReactInitialFile(path='src/App.jsx', content='', editable=True),
                ReactInitialFile(path='src/App.jsx', content='', editable=True),
            )
        )
    with pytest.raises(InvalidActivityError):
        ReactInitialFile(path='src/vite.config.tsx', content='', editable=True)


def test_should_preserve_immutable_react_question_contract() -> None:
    question = _question(policy=_policy())

    assert question.kind == 'react'
    assert question.additional_file_policy is not None
    with pytest.raises(FrozenInstanceError):
        question.prompt = 'changed'  # type: ignore[misc]


def test_should_snapshot_react_policy_and_concept_contract() -> None:
    policy = CurriculumReactAdditionalFilePolicySnapshot(
        allowed_directories=('src/components',),
        allowed_extensions=('.tsx',),
        max_files=4,
    )
    question = CurriculumReactQuestionSnapshot(
        key='react-1',
        prompt='Build a component',
        initial_files=(
            CurriculumReactInitialFileSnapshot(
                path='package.json', content='{}', editable=False
            ),
            CurriculumReactInitialFileSnapshot(
                path='src/App.tsx', content='', editable=True
            ),
        ),
        entrypoint='src/App.tsx',
        fixed_dependencies=(
            CurriculumReactDependencySnapshot(name='react', version='19.0.0'),
        ),
        permitted_commands=(
            CurriculumReactPermittedCommandSnapshot(
                id='dev', executable='npm', arguments=('run', 'dev')
            ),
        ),
        concept_criteria=(),
        additional_file_policy=policy,
    )

    assert question.kind == 'react'
    assert question.additional_file_policy is not None
    assert question.additional_file_policy.allows('src/components/forms/Field.tsx')
    assert not question.additional_file_policy.allows('src/components-old/Field.tsx')
    restored = Serialization.deserialize_value(
        Serialization.serialize_value(question), CurriculumReactQuestionSnapshot
    )
    assert restored == question
    with pytest.raises(ValidationError):
        CurriculumReactInitialFileSnapshot(
            path='src/../App.tsx', content='', editable=True
        )
    with pytest.raises(ValidationError):
        CurriculumReactInitialFileSnapshot(
            path='src/.hidden.tsx', content='', editable=True
        )


def test_should_require_rubric_for_react_and_forbid_react_diagnostics() -> None:
    question = _question()

    with pytest.raises(InvalidActivityError):
        Activity(
            id='activity-1',
            competency_id='competency-1',
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='React activity',
            objective='Build a component',
            questions=(question,),
            evaluation_rule=EvaluationRule(
                parts=(
                    CorrectnessEvaluationPart(
                        question_key=question.key, weight_percentage=100
                    ),
                )
            ),
        )
    with pytest.raises(InvalidActivityError):
        _activity(
            question,
            _rubric_part(question.key),
            activity_type=ActivityType.DIAGNOSTIC,
        )

    activity = _activity(question, _rubric_part(question.key))
    assert activity.questions == (question,)


def test_should_reject_rubric_weight_without_a_required_criterion() -> None:
    criterion = _rubric_part('react-1').criteria[0]
    with pytest.raises(InvalidEvaluationRuleError):
        CodeRubricEvaluationPart(
            question_key='react-1',
            weight_percentage=100,
            criteria=(
                CodeRubricCriterion(
                    key=criterion.key,
                    name=criterion.name,
                    description=criterion.description,
                    weight_percentage=100,
                    required=False,
                    fixed_comments=criterion.fixed_comments,
                    inconclusive_comment=criterion.inconclusive_comment,
                ),
            ),
        )

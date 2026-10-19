from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.entities import CompetencyProgress
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.structures import (
    ChoiceActivityDetail,
    ChoiceQuestionDetail,
    CodeQuestionDetail,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import GetChoiceActivityUseCase
from shifu.shared.core.domain.errors import NotFoundError
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumChoiceActivitySnapshot,
    CurriculumChoiceConceptCriterionSnapshot,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumCompetencySnapshot,
    CurriculumConceptSnapshot,
    CurriculumCodeInconclusiveCommentSnapshot,
    CurriculumCodeRubricCommentSnapshot,
    CurriculumCodeRubricCriterionSnapshot,
    CurriculumCodeRubricPartSnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumReactAdditionalFilePolicySnapshot,
    CurriculumReactDependencySnapshot,
    CurriculumReactInitialFileSnapshot,
    CurriculumReactPermittedCommandSnapshot,
    CurriculumReactQuestionSnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider

ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
SKILL_ID = 'skill-1'
COMPETENCY_ID = 'competency-1'
EXPERIENCE_ID = 'experience-1'
ACTIVITY_ID = 'activity-1'


def snapshot(
    *, explanation: str = 'Feedback privado'
) -> CurriculumChoiceActivitySnapshot:
    questions = tuple(
        CurriculumChoiceQuestionSnapshot(
            key=f'q{index}',
            kind='single_choice' if index == 1 else 'multiple_selection',
            prompt=f'Pergunta {index}?',
            options=(
                CurriculumChoiceOptionSnapshot(key='a', text='A', is_correct=True),
                CurriculumChoiceOptionSnapshot(key='b', text='B', is_correct=False),
                *(
                    (
                        CurriculumChoiceOptionSnapshot(
                            key='c', text='C', is_correct=True
                        ),
                    )
                    if index > 1
                    else ()
                ),
            ),
            correct_explanation=explanation,
            incorrect_explanation='Feedback de revisão',
            concept_criteria=(
                CurriculumChoiceConceptCriterionSnapshot(
                    concept_id=f'concept-{index}',
                    criterion='Critério observável',
                    examples='Exemplo',
                    limits='Limite',
                    correct_score=Decimal('100'),
                    incorrect_score=Decimal('0'),
                ),
            ),
        )
        for index in range(1, 4)
    )
    return CurriculumChoiceActivitySnapshot(
        id=ACTIVITY_ID,
        competency_id=COMPETENCY_ID,
        difficulty='easy',
        title='Atividade',
        questions=questions,
        parts=tuple(
            CurriculumChoicePartSnapshot(
                question_key=f'q{index}',
                weight_percentage=Decimal(weight),
            )
            for index, weight in enumerate(('34', '33', '33'), 1)
        ),
        required_concept_ids=('concept-1', 'concept-2', 'concept-3'),
    )


def react_snapshot() -> CurriculumLearningActivitySnapshot:
    original = snapshot()
    react_question = CurriculumReactQuestionSnapshot(
        key='q3',
        prompt='Crie um componente React',
        initial_files=(
            CurriculumReactInitialFileSnapshot(
                path='src/App.jsx',
                content='export default function App() {}',
                editable=True,
            ),
            CurriculumReactInitialFileSnapshot(
                path='src/style.css', content='body {}', editable=False
            ),
        ),
        entrypoint='src/App.jsx',
        fixed_dependencies=(
            CurriculumReactDependencySnapshot(name='react', version='19.0.0'),
        ),
        permitted_commands=(
            CurriculumReactPermittedCommandSnapshot(
                id='start', executable='npm', arguments=('run', 'dev')
            ),
        ),
        concept_criteria=(),
        additional_file_policy=CurriculumReactAdditionalFilePolicySnapshot(
            allowed_directories=('src/components',),
            allowed_extensions=('.jsx',),
            max_files=2,
        ),
    )
    criterion = CurriculumCodeRubricCriterionSnapshot(
        key='render',
        name='Renderização',
        description='Renderiza o componente',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CurriculumCodeRubricCommentSnapshot(
                id=f'level-{level}', level=level, text=f'Nível {level}'
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CurriculumCodeInconclusiveCommentSnapshot(
            id='inconclusive', text='Inconclusivo'
        ),
    )
    return CurriculumLearningActivitySnapshot(
        id=ACTIVITY_ID,
        competency_id=COMPETENCY_ID,
        difficulty='easy',
        title='Atividade React',
        questions=(*original.questions[:2], react_question),
        parts=(
            *original.parts[:2],
            CurriculumCodeRubricPartSnapshot(
                question_key='q3',
                weight_percentage=original.parts[2].weight_percentage,
                criteria=(criterion,),
            ),
        ),
        required_concept_ids=(),
        activity_type='learning',
        schema_version=1,
        revision='react-2',
    )


class TestGetChoiceActivityUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.provider = create_autospec(CurriculumContentProvider, instance=True)
        self.goal = GoalFaker.fake(id=GOAL_ID, account_id=ACCOUNT_ID)
        self.experience = SkillExperienceFaker.fake(
            id=EXPERIENCE_ID, goal_id=GOAL_ID, skill_id=SKILL_ID
        )
        self.experience.status = SkillExperienceStatus.LEARNING
        self.progress = CompetencyProgress(
            id='progress-1',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            content_released=True,
            created_at=SkillExperienceFaker.fake().created_at,
            updated_at=SkillExperienceFaker.fake().updated_at,
            initial_progress=Decimal('0'),
        )
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.experience
        self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value = self.progress
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = None
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_activity_id.return_value = []
        self.provider.get_choice_activity.return_value = snapshot()
        self.provider.get_skill_content.return_value = CurriculumSkillSnapshot(
            id=SKILL_ID,
            name='Habilidade',
            competencies=(
                CurriculumCompetencySnapshot(
                    id=COMPETENCY_ID,
                    skill_id=SKILL_ID,
                    name='Competência',
                    position=1,
                    concepts=tuple(
                        CurriculumConceptSnapshot(
                            id=f'concept-{index}',
                            competency_id=COMPETENCY_ID,
                            name=f'Conceito {index}',
                            position=index,
                            prerequisite_ids=(),
                            observation_criteria='Critério observável',
                        )
                        for index in range(1, 4)
                    ),
                    items=(
                        CurriculumActivitySnapshot(
                            id=ACTIVITY_ID,
                            title='Atividade',
                            activity_type='learning',
                            difficulty='easy',
                            position=1,
                            concept_ids=('concept-1', 'concept-2', 'concept-3'),
                            required_concept_ids=(
                                'concept-1',
                                'concept-2',
                                'concept-3',
                            ),
                            question_count_by_concept=(
                                ('concept-1', 1),
                                ('concept-2', 1),
                                ('concept-3', 1),
                            ),
                            executable_concept_evidence=True,
                        ),
                    ),
                ),
            ),
        )
        self.subject = GetChoiceActivityUseCase(self.database, self.provider)

    def test_should_return_only_safe_ordered_question_projection(self) -> None:
        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
        )

        assert isinstance(detail, ChoiceActivityDetail)
        assert tuple(question.key for question in detail.questions) == (
            'q1',
            'q2',
            'q3',
        )
        assert isinstance(detail.questions[0], ChoiceQuestionDetail)
        assert tuple(option.key for option in detail.questions[0].options) == ('a', 'b')
        assert detail.can_submit is True
        assert not hasattr(detail.questions[0].options[0], 'is_correct')
        assert not hasattr(detail.questions[0], 'correct_explanation')

    def test_should_not_read_curriculum_for_private_absence(self) -> None:
        self.repositories.goals.find_by_id.return_value = None

        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
            )

        self.provider.get_choice_activity.assert_not_called()

    @pytest.mark.parametrize(
        ('entity', 'attribute', 'other_value'),
        (
            ('goal', 'id', 'another-goal'),
            ('goal', 'account_id', 'another-account'),
            ('experience', 'goal_id', 'another-goal'),
            ('experience', 'skill_id', 'another-skill'),
            ('progress', 'skill_experience_id', 'another-experience'),
            ('progress', 'competency_id', 'another-competency'),
        ),
    )
    def test_should_reject_mismatched_ownership_before_curriculum_lookup(
        self, entity: str, attribute: str, other_value: str
    ) -> None:
        if entity == 'goal' and attribute == 'id':
            self.repositories.goals.find_by_id.return_value = GoalFaker.fake(
                id=other_value, account_id=ACCOUNT_ID
            )
        else:
            setattr(getattr(self, entity), attribute, other_value)

        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
            )

        self.provider.get_learning_activity.assert_not_called()
        self.provider.get_choice_activity.assert_not_called()

    @pytest.mark.parametrize(
        ('activity_id', 'competency_id'),
        (
            ('another-activity', COMPETENCY_ID),
            (ACTIVITY_ID, 'another-competency'),
        ),
    )
    def test_should_reject_mismatched_choice_snapshot_identity(
        self, activity_id: str, competency_id: str
    ) -> None:
        original = snapshot()
        self.provider.get_choice_activity.return_value = (
            CurriculumChoiceActivitySnapshot(
                id=activity_id,
                competency_id=competency_id,
                difficulty=original.difficulty,
                title=original.title,
                questions=original.questions,
                parts=original.parts,
                required_concept_ids=original.required_concept_ids,
            )
        )

        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
            )

        self.provider.get_skill_content.assert_not_called()
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_activity_id.assert_not_called()

    def test_should_reject_unreleased_competency_and_incomplete_snapshot(self) -> None:
        self.progress.content_released = False
        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
            )
        self.provider.get_choice_activity.assert_not_called()

        self.progress.content_released = True
        self.provider.get_choice_activity.return_value = None
        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
            )

    def test_should_project_react_question_and_rubric_without_answer_keys(self) -> None:
        mixed = react_snapshot()
        self.provider.get_learning_activity.return_value = mixed

        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
        )

        assert detail.activity_id == ACTIVITY_ID
        assert detail.title == 'Atividade React'
        assert detail.activity_revision == 'react-2'
        assert tuple(question.key for question in detail.questions) == (
            'q1',
            'q2',
            'q3',
        )
        react_question = mixed.questions[2]
        assert isinstance(react_question, CurriculumReactQuestionSnapshot)
        assert isinstance(detail.questions[2], CodeQuestionDetail)
        code = detail.questions[2]
        assert code.kind == 'react'
        assert code.prompt == 'Crie um componente React'
        assert code.initial_files == react_question.initial_files
        assert code.entrypoint == 'src/App.jsx'
        assert code.editable_paths == ('src/App.jsx',)
        assert code.fixed_dependencies == react_question.fixed_dependencies
        assert code.permitted_commands == react_question.permitted_commands
        assert tuple(
            (item.key, item.name, item.weight_percentage) for item in code.criteria
        ) == (('render', 'Renderização', 100),)
        assert code.additional_file_policy == react_question.additional_file_policy
        assert detail.can_submit is True
        self.provider.get_learning_activity.assert_called_once_with(ACTIVITY_ID)
        self.provider.get_choice_activity.assert_not_called()
        self.provider.get_skill_content.assert_not_called()

    def test_should_fall_back_to_choice_when_mixed_snapshot_has_no_code(self) -> None:
        original = snapshot()
        self.provider.get_learning_activity.return_value = (
            CurriculumLearningActivitySnapshot(
                id=original.id,
                competency_id=original.competency_id,
                difficulty=original.difficulty,
                title='Choice in mixed catalog',
                questions=original.questions,
                parts=original.parts,
                required_concept_ids=original.required_concept_ids,
                activity_type='learning',
                schema_version=1,
                revision='choice-2',
            )
        )

        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
        )

        assert detail.title == 'Atividade'
        self.provider.get_learning_activity.assert_called_once_with(ACTIVITY_ID)
        self.provider.get_choice_activity.assert_called_once_with(ACTIVITY_ID)
        self.provider.get_skill_content.assert_called_once_with(SKILL_ID)

    def test_should_reject_mixed_snapshot_for_another_competency(self) -> None:
        mixed = react_snapshot()
        self.provider.get_learning_activity.return_value = (
            CurriculumLearningActivitySnapshot(
                id=mixed.id,
                competency_id='another-competency',
                difficulty=mixed.difficulty,
                title=mixed.title,
                questions=mixed.questions,
                parts=mixed.parts,
                required_concept_ids=mixed.required_concept_ids,
                activity_type=mixed.activity_type,
                schema_version=mixed.schema_version,
                revision=mixed.revision,
            )
        )

        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
            )

        self.provider.get_choice_activity.assert_not_called()
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_activity_id.assert_not_called()

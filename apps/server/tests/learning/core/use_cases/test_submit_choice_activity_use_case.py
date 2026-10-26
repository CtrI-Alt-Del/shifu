from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.entities import CompetencyProgress
from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.structures import (
    ActivityAnswer,
    ChoiceAnswerSubmission,
    CodeAnswer,
    CodeSubmittedFile,
    MultipleSelectionAnswer,
    SingleChoiceAnswer,
)
from tests.learning.core.use_cases.test_preview_activity_question_feedback_use_case import (
    mixed_snapshot,
    code_answer_at_size,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import SubmitChoiceActivityUseCase
from shifu.shared.core.domain.errors import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumChoiceActivitySnapshot,
    CurriculumChoiceConceptCriterionSnapshot,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumCodeInconclusiveCommentSnapshot,
    CurriculumCodeRubricCommentSnapshot,
    CurriculumCodeRubricCriterionSnapshot,
    CurriculumCodeRubricPartSnapshot,
    CurriculumCompetencySnapshot,
    CurriculumConceptSnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumReactAdditionalFilePolicySnapshot,
    CurriculumReactInitialFileSnapshot,
    CurriculumReactQuestionSnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)

ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
SKILL_ID = 'skill-1'
COMPETENCY_ID = 'competency-1'
EXPERIENCE_ID = 'experience-1'
ACTIVITY_ID = 'activity-1'
NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)


def choice_snapshot() -> CurriculumChoiceActivitySnapshot:
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
            correct_explanation='Correta',
            incorrect_explanation='Incorreta',
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


def answers() -> tuple[ChoiceAnswerSubmission, ...]:
    return (
        ChoiceAnswerSubmission(question_key='q1', selected_option_keys=('a',)),
        ChoiceAnswerSubmission(question_key='q2', selected_option_keys=('c', 'a')),
        ChoiceAnswerSubmission(question_key='q3', selected_option_keys=('a',)),
    )


def react_activity_snapshot() -> CurriculumLearningActivitySnapshot:
    choice_questions = choice_snapshot().questions[:2]
    react_question = CurriculumReactQuestionSnapshot(
        key='q3',
        prompt='Build a React component',
        initial_files=(
            CurriculumReactInitialFileSnapshot(
                path='src/main.tsx', content='old', editable=True
            ),
            CurriculumReactInitialFileSnapshot(
                path='src/fixed.css', content='fixed', editable=False
            ),
        ),
        entrypoint='src/main.tsx',
        fixed_dependencies=(),
        permitted_commands=(),
        concept_criteria=(),
        additional_file_policy=CurriculumReactAdditionalFilePolicySnapshot(
            allowed_directories=('src/components',),
            allowed_extensions=('.tsx', '.css'),
            max_files=2,
        ),
    )
    criterion = CurriculumCodeRubricCriterionSnapshot(
        key='quality',
        name='Qualidade',
        description='Implementação',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CurriculumCodeRubricCommentSnapshot(
                id=f'level-{level}', level=level, text=f'Comentário {level}'
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CurriculumCodeInconclusiveCommentSnapshot(
            id='unknown', text='Inconclusivo'
        ),
    )
    return CurriculumLearningActivitySnapshot(
        id=ACTIVITY_ID,
        competency_id=COMPETENCY_ID,
        difficulty='easy',
        title='Atividade React',
        questions=(*choice_questions, react_question),
        parts=(
            CurriculumChoicePartSnapshot(
                question_key='q1', weight_percentage=Decimal(30)
            ),
            CurriculumChoicePartSnapshot(
                question_key='q2', weight_percentage=Decimal(30)
            ),
            CurriculumCodeRubricPartSnapshot(
                question_key='q3',
                weight_percentage=Decimal(40),
                criteria=(criterion,),
            ),
        ),
        required_concept_ids=('concept-1', 'concept-2'),
        activity_type='learning',
        schema_version=1,
        revision='revision-react-1',
    )


class TestSubmitChoiceActivityUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.provider = create_autospec(CurriculumContentProvider, instance=True)
        self.clock = create_autospec(ClockProvider, instance=True)
        self.ids = create_autospec(IdentifierProvider, instance=True)
        self.ids.generate.side_effect = ('attempt-1', 'evaluation-1', 'run-1')
        self.clock.now.return_value = NOW
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
            created_at=NOW,
            updated_at=NOW,
            initial_progress=Decimal('0'),
        )
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.experience
        self.repositories.skill_experiences.find_by_id_for_update.return_value = (
            self.experience
        )
        self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value = self.progress
        self.repositories.activity_attempts.find_by_skill_experience_id_and_submission_key.return_value = None
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = None
        self.provider.get_choice_activity.return_value = choice_snapshot()
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
        self.subject = SubmitChoiceActivityUseCase(
            self.database, self.provider, self.clock, self.ids
        )

    @pytest.mark.parametrize(
        ('changed', 'error_type'),
        (
            ('goal', NotFoundError),
            ('experience', NotFoundError),
            ('progress', NotFoundError),
            ('release', NotFoundError),
            ('not-started', NotFoundError),
            ('diagnosing', ConflictError),
        ),
    )
    def test_should_revalidate_ownership_and_learning_state_before_persistence(
        self,
        changed: str,
        error_type: type[NotFoundError] | type[ConflictError],
    ) -> None:
        if changed == 'goal':
            self.repositories.goals.find_by_id.side_effect = (self.goal, None)
        elif changed == 'experience':
            self.repositories.skill_experiences.find_by_id_for_update.return_value = (
                None
            )
        elif changed == 'progress':
            self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value = None
        elif changed == 'release':
            self.progress.content_released = False
        else:
            self.repositories.skill_experiences.find_by_id_for_update.return_value = (
                SkillExperienceFaker.fake(
                    id=EXPERIENCE_ID,
                    goal_id=GOAL_ID,
                    skill_id=SKILL_ID,
                    status=SkillExperienceStatus(changed),
                )
            )

        with pytest.raises(error_type):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                'submission-key',
                answers(),
            )

        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.activity_evaluations.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reject_blank_submission_key_before_reading_private_data(
        self,
    ) -> None:
        with pytest.raises(ValidationError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                '  ',
                answers(),
            )

        self.database.transaction.assert_not_called()
        self.provider.get_learning_activity.assert_not_called()

    def test_should_persist_one_immutable_attempt_evaluation_and_handoff(self) -> None:
        detail = self.subject.execute(
            ACCOUNT_ID,
            GOAL_ID,
            SKILL_ID,
            COMPETENCY_ID,
            ACTIVITY_ID,
            'submission-key',
            answers(),
        )

        assert detail.attempt.attempt_id == 'attempt-1'
        assert detail.attempt.status is ActivityEvaluationStatus.PENDING
        assert detail.replayed is False
        attempt = self.repositories.activity_attempts.add.call_args.args[0]

        assert attempt.answers == (
            SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
            MultipleSelectionAnswer(question_key='q2', selected_option_keys=('c', 'a')),
            MultipleSelectionAnswer(question_key='q3', selected_option_keys=('a',)),
        )
        assert attempt.submission_key == 'submission-key'
        assert attempt.grading_snapshot.id == ACTIVITY_ID
        evaluation = self.repositories.activity_evaluations.add.call_args.args[0]

        assert evaluation.run_id == 'run-1'
        event = self.repositories.events.add.call_args.args[0]

        assert event.payload.attempt_id == attempt.id
        assert event.payload.run_id == evaluation.run_id

    def test_should_reject_incomplete_answers_without_writing(self) -> None:
        with pytest.raises(ValidationError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                'submission-key',
                answers()[:-1],
            )

        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_submit_react_files_as_part_of_existing_attempt(self) -> None:
        snapshot = react_activity_snapshot()
        self.provider.get_learning_activity.return_value = snapshot
        submitted_answers = (
            *answers()[:2],
            CodeAnswer(
                question_key='q3',
                kind='react',
                files=(
                    CodeSubmittedFile(path='src/main.tsx', content='updated'),
                    CodeSubmittedFile(
                        path='src/components/Card.tsx',
                        content='export const Card = () => null',
                    ),
                ),
            ),
        )

        outcome = self.subject.execute(
            ACCOUNT_ID,
            GOAL_ID,
            SKILL_ID,
            COMPETENCY_ID,
            ACTIVITY_ID,
            'react-submission',
            submitted_answers,
            snapshot.revision,
        )

        attempt = self.repositories.activity_attempts.add.call_args.args[0]
        assert outcome.replayed is False
        assert attempt.answers[-1] == CodeAnswer(
            question_key='q3',
            kind='react',
            files=(
                CodeSubmittedFile(
                    path='src/components/Card.tsx',
                    content='export const Card = () => null',
                ),
                CodeSubmittedFile(path='src/main.tsx', content='updated'),
            ),
        )
        assert attempt.grading_snapshot is snapshot
        question = snapshot.questions[-1]
        assert isinstance(question, CurriculumReactQuestionSnapshot)
        assert question.kind == 'react'
        assert question.additional_file_policy is not None
        with pytest.raises(FrozenInstanceError):
            question.prompt = 'changed'  # type: ignore[misc]
        assert snapshot.questions[-1] is question
        self.repositories.events.add.assert_called_once()

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
            'src/components-old/Button.tsx',
            'src/Other.tsx',
            'src/components/Button.js',
        ),
    )
    def test_should_reject_noncanonical_additional_react_paths_before_writes(
        self,
        path: str,
    ) -> None:
        snapshot = react_activity_snapshot()
        self.provider.get_learning_activity.return_value = snapshot
        with pytest.raises(ValidationError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                'unsafe-react-path',
                (
                    *answers()[:2],
                    CodeAnswer(
                        question_key='q3',
                        kind='react',
                        files=(
                            CodeSubmittedFile(path='src/main.tsx', content='main'),
                            CodeSubmittedFile(path=path, content='extra'),
                        ),
                    ),
                ),
                snapshot.revision,
            )
        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.activity_evaluations.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reject_tampered_react_file_policy_without_side_effects(
        self,
    ) -> None:
        snapshot = react_activity_snapshot()
        self.provider.get_learning_activity.return_value = snapshot
        submitted_answers = (
            *answers()[:2],
            CodeAnswer(
                question_key='q3',
                kind='react',
                files=(
                    CodeSubmittedFile(path='src/main.tsx', content='updated'),
                    CodeSubmittedFile(path='src/components/package.json', content='{}'),
                ),
            ),
        )

        with pytest.raises(ValidationError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                'react-submission',
                submitted_answers,
                snapshot.revision,
            )

        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.activity_evaluations.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_accept_exact_react_additional_file_limit_and_normalize_kind(
        self,
    ) -> None:
        snapshot = react_activity_snapshot()
        self.provider.get_learning_activity.return_value = snapshot

        outcome = self.subject.execute(
            ACCOUNT_ID,
            GOAL_ID,
            SKILL_ID,
            COMPETENCY_ID,
            ACTIVITY_ID,
            'react-two-additional-files',
            (
                *answers()[:2],
                CodeAnswer(
                    question_key='q3',
                    files=(
                        CodeSubmittedFile(path='src/main.tsx', content='updated'),
                        CodeSubmittedFile(path='src/components/Z.css', content='z'),
                        CodeSubmittedFile(path='src/components/A.tsx', content='a'),
                    ),
                ),
            ),
            snapshot.revision,
        )

        assert outcome.attempt.status is ActivityEvaluationStatus.PENDING
        attempt = self.repositories.activity_attempts.add.call_args.args[0]
        assert attempt.answers[-1] == CodeAnswer(
            question_key='q3',
            kind='react',
            files=(
                CodeSubmittedFile(path='src/components/A.tsx', content='a'),
                CodeSubmittedFile(path='src/components/Z.css', content='z'),
                CodeSubmittedFile(path='src/main.tsx', content='updated'),
            ),
        )
        self.repositories.activity_evaluations.add.assert_called_once()
        self.repositories.events.add.assert_called_once()

    @pytest.mark.parametrize(
        'code_answer',
        (
            CodeAnswer(question_key='q3', kind='react', files=()),
            CodeAnswer(
                question_key='q3',
                kind='react',
                source_code='untrusted replacement',
                files=(CodeSubmittedFile(path='src/main.tsx', content='updated'),),
            ),
            CodeAnswer(
                question_key='q3',
                kind='javascript_stdin',
                files=(CodeSubmittedFile(path='src/main.tsx', content='updated'),),
            ),
            CodeAnswer(
                question_key='q3',
                kind='react',
                files=(
                    CodeSubmittedFile(path='src/main.tsx', content='first'),
                    CodeSubmittedFile(path='src/main.tsx', content='second'),
                ),
            ),
            CodeAnswer(
                question_key='q3',
                kind='react',
                files=(CodeSubmittedFile(path='src/fixed.css', content='tampered'),),
            ),
            CodeAnswer(
                question_key='q3',
                kind='react',
                files=(
                    CodeSubmittedFile(path='src/main.tsx', content='updated'),
                    CodeSubmittedFile(path='src/fixed.css', content='tampered'),
                ),
            ),
            CodeAnswer(
                question_key='q3',
                kind='react',
                files=(
                    CodeSubmittedFile(path='src/main.tsx', content='updated'),
                    CodeSubmittedFile(path='src/components/A.tsx', content='a'),
                    CodeSubmittedFile(path='src/components/B.tsx', content='b'),
                    CodeSubmittedFile(path='src/components/C.tsx', content='c'),
                ),
            ),
            CodeAnswer(
                question_key='q3',
                kind='react',
                files=(
                    CodeSubmittedFile(path='src/main.tsx', content='updated'),
                    CodeSubmittedFile(path='src/components/package.json', content='{}'),
                ),
            ),
        ),
        ids=(
            'missing-editable',
            'legacy-source',
            'wrong-kind',
            'duplicate-path',
            'readonly-instead-of-editable',
            'readonly-overwrite',
            'additional-limit',
            'forbidden-configuration',
        ),
    )
    def test_should_reject_invalid_react_projects_before_any_write(
        self, code_answer: CodeAnswer
    ) -> None:
        snapshot = react_activity_snapshot()
        self.provider.get_learning_activity.return_value = snapshot

        with pytest.raises(ValidationError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                'invalid-react-project',
                (*answers()[:2], code_answer),
                snapshot.revision,
            )

        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.activity_evaluations.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    @pytest.mark.parametrize('react', (False, True), ids=('javascript', 'react'))
    @pytest.mark.parametrize(
        'limit', (128, 256 * 1024, 512 * 1024), ids=('lower', 'default', 'higher')
    )
    @pytest.mark.parametrize('extra_byte', (0, 1), ids=('exact', 'above'))
    def test_should_apply_configured_utf8_project_limit_to_submit_and_replay(
        self, react: bool, limit: int, extra_byte: int
    ) -> None:
        snapshot = mixed_snapshot(react=react)
        question = snapshot.questions[-1]
        assert isinstance(
            question,
            (
                CurriculumJavascriptStdinQuestionSnapshot,
                CurriculumReactQuestionSnapshot,
            ),
        )
        self.provider.get_learning_activity.return_value = snapshot
        subject = SubmitChoiceActivityUseCase(
            self.database, self.provider, self.clock, self.ids, limit
        )
        submitted = (
            ChoiceAnswerSubmission(question_key='q1', selected_option_keys=('a',)),
            ChoiceAnswerSubmission(question_key='q2', selected_option_keys=('a',)),
            code_answer_at_size(question, limit + extra_byte),
        )
        arguments = (
            ACCOUNT_ID,
            GOAL_ID,
            SKILL_ID,
            COMPETENCY_ID,
            ACTIVITY_ID,
            'configured-limit',
            submitted,
            snapshot.revision,
        )

        if extra_byte:
            with pytest.raises(ValidationError):
                subject.execute(*arguments)
            self.repositories.activity_attempts.add.assert_not_called()
            self.repositories.activity_evaluations.add.assert_not_called()
            self.repositories.events.add.assert_not_called()
            return

        created = subject.execute(*arguments)
        saved = self.repositories.activity_attempts.add.call_args.args[0]
        evaluation = self.repositories.activity_evaluations.add.call_args.args[0]
        self.repositories.activity_attempts.find_by_skill_experience_id_and_submission_key.return_value = saved
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = (
            evaluation
        )

        replayed = subject.execute(*arguments)

        assert not created.replayed
        assert replayed.replayed
        assert replayed.attempt.attempt_id == created.attempt.attempt_id
        self.repositories.activity_attempts.add.assert_called_once()
        self.repositories.events.add.assert_called_once()

    @pytest.mark.parametrize('length', (240, 241))
    def test_should_accept_only_canonical_additional_paths_at_the_path_limit(
        self, length: int
    ) -> None:
        snapshot = react_activity_snapshot()
        prefix = 'src/components/' + ('a' * 64 + '/') * 3
        path = prefix + 'b' * (length - len(prefix) - 4) + '.tsx'
        submitted = (
            *answers()[:2],
            CodeAnswer(
                question_key='q3',
                kind='react',
                files=(
                    CodeSubmittedFile(path='src/main.tsx', content='main'),
                    CodeSubmittedFile(path=path, content='extra'),
                ),
            ),
        )

        if length == 241:
            with pytest.raises(ValidationError):
                SubmitChoiceActivityUseCase.normalize_answers(snapshot, submitted)
        else:
            normalized = SubmitChoiceActivityUseCase.normalize_answers(
                snapshot, submitted
            )
            code = normalized[-1]
            assert isinstance(code, CodeAnswer)
            assert path in {item.path for item in code.files}

    @pytest.mark.parametrize('additional', (False, True))
    def test_should_allow_only_initial_files_without_an_additional_file_policy(
        self, additional: bool
    ) -> None:
        snapshot = react_activity_snapshot()
        question = snapshot.questions[-1]
        assert isinstance(question, CurriculumReactQuestionSnapshot)
        snapshot = replace(
            snapshot,
            questions=(
                *snapshot.questions[:-1],
                replace(question, additional_file_policy=None),
            ),
        )
        code = CodeAnswer(
            question_key='q3',
            kind='react',
            files=(
                CodeSubmittedFile(path='src/main.tsx', content='main'),
                *(
                    (
                        CodeSubmittedFile(
                            path='src/components/Extra.tsx', content='extra'
                        ),
                    )
                    if additional
                    else ()
                ),
            ),
        )

        if additional:
            with pytest.raises(ValidationError):
                SubmitChoiceActivityUseCase.normalize_answers(
                    snapshot, (*answers()[:2], code)
                )
        else:
            normalized = SubmitChoiceActivityUseCase.normalize_answers(
                snapshot, (*answers()[:2], code)
            )
            assert normalized[-1] == code

    def test_should_reject_v2_choice_without_trusted_live_concept_criteria(
        self,
    ) -> None:
        self.experience.status = SkillExperienceStatus.LEARNING
        self.provider.get_skill_content.return_value = None

        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                'submission-key',
                answers(),
            )

        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reject_diagnostic_replay_after_experience_enters_learning(
        self,
    ) -> None:
        from shifu.learning.core.domain.entities import ActivityAttempt
        from shifu.learning.core.domain.enums import ActivityAttemptKind

        self.experience.status = SkillExperienceStatus.LEARNING
        snapshot = choice_snapshot()
        diagnostic_snapshot = CurriculumChoiceActivitySnapshot(
            id=snapshot.id,
            competency_id=snapshot.competency_id,
            difficulty=snapshot.difficulty,
            title=snapshot.title,
            questions=snapshot.questions,
            parts=snapshot.parts,
            activity_type='diagnostic',
        )
        attempt = ActivityAttempt.create(
            id='attempt-prior',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.DIAGNOSTIC,
            answers=(
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                MultipleSelectionAnswer(
                    question_key='q2', selected_option_keys=('c', 'a')
                ),
                MultipleSelectionAnswer(question_key='q3', selected_option_keys=('a',)),
            ),
            submitted_at=NOW,
            submission_key='submission-key',
            diagnostic_run_id='diagnostic-run',
            grading_snapshot=diagnostic_snapshot,
        )
        self.repositories.activity_attempts.find_by_skill_experience_id_and_submission_key.return_value = attempt

        with pytest.raises(ConflictError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                'submission-key',
                answers(),
                diagnostic_run_id='diagnostic-run',
            )

        self.provider.get_choice_activity.assert_not_called()
        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_reuse_matching_key_and_reject_different_payload(self) -> None:
        prior = self.repositories.activity_attempts.find_by_skill_experience_id_and_submission_key
        from shifu.learning.core.domain.entities import (
            ActivityAttempt,
            ActivityEvaluation,
        )
        from shifu.learning.core.domain.enums import ActivityAttemptKind

        attempt = ActivityAttempt.create(
            id='attempt-prior',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=ActivityAttemptKind.LEARNING,
            answers=(
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                MultipleSelectionAnswer(
                    question_key='q2', selected_option_keys=('c', 'a')
                ),
                MultipleSelectionAnswer(question_key='q3', selected_option_keys=('a',)),
            ),
            submitted_at=NOW,
            submission_key='submission-key',
            grading_snapshot=choice_snapshot(),
        )
        evaluation = ActivityEvaluation.create(
            id='evaluation-prior',
            attempt_id=attempt.id,
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=NOW,
            run_id='run-prior',
        )
        prior.return_value = attempt
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = (
            evaluation
        )
        replay = self.subject.execute(
            ACCOUNT_ID,
            GOAL_ID,
            SKILL_ID,
            COMPETENCY_ID,
            ACTIVITY_ID,
            'submission-key',
            answers(),
        )

        assert replay.attempt.attempt_id == attempt.id
        assert replay.replayed is True
        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

        with pytest.raises(ConflictError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                'submission-key',
                (
                    ChoiceAnswerSubmission(
                        question_key='q1', selected_option_keys=('b',)
                    ),
                    *answers()[1:],
                ),
            )

    def test_should_reject_multiple_keys_for_single_choice(self) -> None:
        with pytest.raises(ValidationError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                'submission-key',
                (
                    ChoiceAnswerSubmission(
                        question_key='q1', selected_option_keys=('a', 'b')
                    ),
                    *answers()[1:],
                ),
            )

        self.repositories.activity_attempts.add.assert_not_called()

    def test_should_reject_private_absence_without_curriculum_read(self) -> None:
        self.repositories.goals.find_by_id.return_value = None

        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID,
                GOAL_ID,
                SKILL_ID,
                COMPETENCY_ID,
                ACTIVITY_ID,
                'key',
                answers(),
            )

        self.provider.get_choice_activity.assert_not_called()

    def test_should_address_every_collaborator_with_the_requested_identity(
        self,
    ) -> None:
        """Submission resolves ownership and replay from the request's own
        identifiers; a wrong one would attach the attempt to another learner."""
        self.subject.execute(
            ACCOUNT_ID,
            GOAL_ID,
            SKILL_ID,
            COMPETENCY_ID,
            ACTIVITY_ID,
            'submission-key',
            answers(),
        )

        self.repositories.goals.find_by_id.assert_called_with(GOAL_ID)
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.assert_called_with(
            GOAL_ID, SKILL_ID
        )
        self.repositories.activity_attempts.find_by_skill_experience_id_and_submission_key.assert_called_with(
            self.experience.id, 'submission-key'
        )
        self.repositories.skill_experiences.find_by_id_for_update.assert_called_with(
            self.experience.id
        )
        self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.assert_called_with(
            self.experience.id, COMPETENCY_ID
        )
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.assert_called_with(
            self.experience.id
        )

    def test_should_persist_the_attempt_under_the_resolved_experience(self) -> None:
        self.subject.execute(
            ACCOUNT_ID,
            GOAL_ID,
            SKILL_ID,
            COMPETENCY_ID,
            ACTIVITY_ID,
            'submission-key',
            answers(),
        )

        attempt = self.repositories.activity_attempts.add.call_args.args[0]
        assert attempt.skill_experience_id == self.experience.id
        assert attempt.competency_id == COMPETENCY_ID
        assert attempt.activity_id == ACTIVITY_ID
        assert attempt.id == 'attempt-1'

        evaluation = self.repositories.activity_evaluations.add.call_args.args[0]
        assert evaluation.attempt_id == attempt.id
        assert evaluation.status is ActivityEvaluationStatus.PENDING

    def test_should_publish_the_handoff_event_for_the_saved_attempt(self) -> None:
        self.subject.execute(
            ACCOUNT_ID,
            GOAL_ID,
            SKILL_ID,
            COMPETENCY_ID,
            ACTIVITY_ID,
            'submission-key',
            answers(),
        )

        attempt = self.repositories.activity_attempts.add.call_args.args[0]
        evaluation = self.repositories.activity_evaluations.add.call_args.args[0]
        event = self.repositories.events.add.call_args.args[0]
        assert event.payload.attempt_id == attempt.id
        assert event.payload.run_id == evaluation.run_id


class TestSubmitChoiceActivityAnswerNormalization:
    """`normalize_answers` is the submission boundary's validation surface: it
    decides which payloads are allowed to become an immutable attempt."""

    @staticmethod
    def _choice() -> tuple[ChoiceAnswerSubmission, ...]:
        return (
            ChoiceAnswerSubmission(question_key='q1', selected_option_keys=('a',)),
            ChoiceAnswerSubmission(question_key='q2', selected_option_keys=('a',)),
        )

    def _submit(self, code: CodeAnswer) -> tuple[ActivityAnswer, ...]:
        return SubmitChoiceActivityUseCase.normalize_answers(
            mixed_snapshot(), (*self._choice(), code)
        )

    def test_should_sort_editable_files_by_path(self) -> None:
        normalized = SubmitChoiceActivityUseCase.normalize_answers(
            mixed_snapshot(),
            (
                *self._choice(),
                CodeAnswer(
                    question_key='q3',
                    files=(CodeSubmittedFile(path='src/main.js', content='new'),),
                ),
            ),
        )

        code = normalized[2]
        assert isinstance(code, CodeAnswer)
        assert code.question_key == 'q3'
        assert [item.path for item in code.files] == ['src/main.js']

    def test_should_reject_a_code_answer_carrying_inline_source(self) -> None:
        with pytest.raises(ValidationError):
            self._submit(
                CodeAnswer(
                    question_key='q3',
                    source_code='console.log(1)',
                    files=(CodeSubmittedFile(path='src/main.js', content='new'),),
                )
            )

    def test_should_reject_duplicated_file_paths(self) -> None:
        with pytest.raises(ValidationError):
            self._submit(
                CodeAnswer(
                    question_key='q3',
                    files=(
                        CodeSubmittedFile(path='src/main.js', content='a'),
                        CodeSubmittedFile(path='src/main.js', content='b'),
                    ),
                )
            )

    def test_should_reject_writing_outside_the_editable_files(self) -> None:
        with pytest.raises(ValidationError):
            self._submit(
                CodeAnswer(
                    question_key='q3',
                    files=(CodeSubmittedFile(path='src/lib.js', content='hack'),),
                )
            )

    def test_should_reject_a_partial_editable_file_set(self) -> None:
        with pytest.raises(ValidationError):
            self._submit(CodeAnswer(question_key='q3', files=()))

    def test_should_reject_a_choice_answer_for_a_code_question(self) -> None:
        with pytest.raises(ValidationError):
            SubmitChoiceActivityUseCase.normalize_answers(
                mixed_snapshot(),
                (
                    *self._choice(),
                    ChoiceAnswerSubmission(
                        question_key='q3', selected_option_keys=('a',)
                    ),
                ),
            )

    def test_should_reject_a_code_answer_for_a_choice_question(self) -> None:
        with pytest.raises(ValidationError):
            SubmitChoiceActivityUseCase.normalize_answers(
                mixed_snapshot(),
                (
                    CodeAnswer(question_key='q1', files=()),
                    ChoiceAnswerSubmission(
                        question_key='q2', selected_option_keys=('a',)
                    ),
                    CodeAnswer(
                        question_key='q3',
                        files=(CodeSubmittedFile(path='src/main.js', content='n'),),
                    ),
                ),
            )

    def test_should_reject_answers_out_of_order_or_short(self) -> None:
        with pytest.raises(ValidationError):
            SubmitChoiceActivityUseCase.normalize_answers(
                mixed_snapshot(), self._choice()
            )
        with pytest.raises(ValidationError):
            SubmitChoiceActivityUseCase.normalize_answers(
                mixed_snapshot(),
                (
                    ChoiceAnswerSubmission(
                        question_key='q2', selected_option_keys=('a',)
                    ),
                    ChoiceAnswerSubmission(
                        question_key='q1', selected_option_keys=('a',)
                    ),
                    CodeAnswer(
                        question_key='q3',
                        files=(CodeSubmittedFile(path='src/main.js', content='n'),),
                    ),
                ),
            )

from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager, nullcontext
from dataclasses import fields, replace
from decimal import ROUND_HALF_UP, Decimal
from itertools import permutations
from typing import TYPE_CHECKING, Any
from unittest.mock import create_autospec
from uuid import UUID

import httpx
import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.fakers.shared.curriculum_fill_blanks_question_snapshot_faker import (
    CurriculumFillBlanksQuestionSnapshotFaker,
)
from shifu.fakers.shared.curriculum_fill_blanks_activity_snapshot_faker import (
    CurriculumFillBlanksActivitySnapshotFaker,
)
from shifu.fakers.shared.curriculum_pair_matching_question_snapshot_faker import (
    CurriculumPairMatchingQuestionSnapshotFaker,
)
from shifu.intelligence.providers.code_rubric_assessor.jev.jev_code_rubric_assessor_provider import (
    JevCodeRubricAssessorProvider,
)
from shifu.learning.core.domain.entities import CompetencyProgress, OrderingPassage
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.structures import (
    ChoiceAnswerSubmission,
    CodeAnswer,
    CodeSubmittedFile,
    FillBlanksAnswer,
    FillBlanksPlacement,
    PairMatchingAnswer,
    PairMatchingSelection,
    TranslationAnswer,
    VerifiedOrdering,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.preview_activity_question_feedback_use_case import (
    PreliminaryQuestionResult,
    PreviewActivityQuestionFeedbackUseCase,
)
from shifu.shared.core.domain.errors import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from shifu.shared.core.interfaces import (
    AccountActivityProvider,
    CodeRubricAssessorProvider,
    CurriculumContentProvider,
    IdentifierProvider,
    TranslationRubricAssessorProvider,
)
from shifu.shared.core.domain.structures import (
    CurriculumFillBlanksBlankSnapshot,
    CurriculumFillBlanksConceptCriterionSnapshot,
    CurriculumFillBlanksSegmentSnapshot,
    CurriculumFillBlanksWordSnapshot,
    CodeCriterionDecision,
    CodeRubricDecisions,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumCodeInconclusiveCommentSnapshot,
    CurriculumCodeRubricCommentSnapshot,
    CurriculumCodeRubricCriterionSnapshot,
    CurriculumCodeRubricPartSnapshot,
    CurriculumJavascriptInitialFileSnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumReactAdditionalFilePolicySnapshot,
    CurriculumReactInitialFileSnapshot,
    CurriculumReactQuestionSnapshot,
    CurriculumReactFastifyQuestionSnapshot,
    CurriculumReactDependencySnapshot,
    CurriculumReactPermittedCommandSnapshot,
    CurriculumReactFastifyHttpExampleSnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumOrderingQuestionSnapshot,
    CurriculumOrderingStepSnapshot,
    CurriculumPairMatchingItemSnapshot,
    CurriculumPairMatchingPairSnapshot,
    CurriculumChoiceConceptCriterionSnapshot,
    CurriculumTranslationInconclusiveCommentSnapshot,
    CurriculumTranslationQuestionSnapshot,
    CurriculumTranslationRubricCommentSnapshot,
    CurriculumTranslationRubricCriterionSnapshot,
    CurriculumTranslationRubricPartSnapshot,
)
if TYPE_CHECKING:
    from collections.abc import Generator
    from shifu.shared.core.domain.structures.code_rubric_decisions import (
        CodeRubricLevel,
    )


@contextmanager
def _admit_external_effect(
    _account_id: str, _effect_id: UUID, _operation: str
) -> Generator[bool]:
    yield True


def _grade(correct: int, total: int) -> Decimal:
    """100 x correct / total, rounded half up to two decimals."""
    return (Decimal(100) * correct / Decimal(total)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )


def mixed_snapshot(*, react: bool | str = False) -> CurriculumLearningActivitySnapshot:
    choice = tuple(
        CurriculumChoiceQuestionSnapshot(
            key=f'q{number}',
            kind='single_choice',
            prompt='Choose',
            options=(
                CurriculumChoiceOptionSnapshot(key='a', text='A', is_correct=True),
            ),
            correct_explanation='Correct',
            incorrect_explanation='Wrong',
        )
        for number in (1, 2)
    )
    code = (
        CurriculumReactQuestionSnapshot(
            key='q3',
            prompt='Build a component',
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
        if react
        else CurriculumJavascriptStdinQuestionSnapshot(
            key='q3',
            prompt='Read stdin',
            initial_files=(
                CurriculumJavascriptInitialFileSnapshot(
                    path='src/main.js', content='old', editable=True
                ),
                CurriculumJavascriptInitialFileSnapshot(
                    path='src/lib.js', content='fixed', editable=False
                ),
            ),
            entrypoint='src/main.js',
            fixed_dependencies=(),
            permitted_commands=(),
            concept_criteria=(),
        )
    )
    if react == 'integrated':
        assert isinstance(code, CurriculumReactQuestionSnapshot)
        code = integrated_question(code)
    criterion = CurriculumCodeRubricCriterionSnapshot(
        key='correctness',
        name='Correctness',
        description='Output',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CurriculumCodeRubricCommentSnapshot(
                id=f'level-{level}', level=level, text=f'Comment {level}'
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CurriculumCodeInconclusiveCommentSnapshot(
            id='unknown', text='Unknown'
        ),
    )
    return CurriculumLearningActivitySnapshot(
        id='activity-1',
        competency_id='competency-1',
        difficulty='easy',
        title='Mixed',
        questions=(*choice, code),
        parts=(
            CurriculumChoicePartSnapshot(
                question_key='q1', weight_percentage=Decimal(30)
            ),
            CurriculumChoicePartSnapshot(
                question_key='q2', weight_percentage=Decimal(30)
            ),
            CurriculumCodeRubricPartSnapshot(
                question_key='q3', weight_percentage=Decimal(40), criteria=(criterion,)
            ),
        ),
        required_concept_ids=(),
        activity_type='learning',
        schema_version=1,
        revision='revision-1',
    )


def integrated_question(
    original: CurriculumReactQuestionSnapshot,
) -> CurriculumReactFastifyQuestionSnapshot:
    return CurriculumReactFastifyQuestionSnapshot(
        key=original.key,
        prompt=original.prompt,
        initial_files=(
            *original.initial_files,
            CurriculumReactInitialFileSnapshot(
                path='routes/api.js',
                content='api',
                editable=True,
            ),
        ),
        frontend_entrypoint=original.entrypoint,
        api_entrypoint='routes/api.js',
        fixed_dependencies=tuple(
            CurriculumReactDependencySnapshot(name=name, version=version)
            for name, version in (
                ('react', '19.2.0'),
                ('react-dom', '19.2.0'),
                ('vite', '8.3.0'),
                ('fastify', '5.6.2'),
            )
        ),
        permitted_commands=(
            CurriculumReactPermittedCommandSnapshot(
                id='web', executable='npm', arguments=('run', 'dev:web')
            ),
            CurriculumReactPermittedCommandSnapshot(
                id='api', executable='npm', arguments=('run', 'dev:api')
            ),
        ),
        frontend_command_id='web',
        api_command_id='api',
        http_examples=(
            CurriculumReactFastifyHttpExampleSnapshot(
                key='tasks', title='Listar tarefas', method='GET', path='/api/tasks'
            ),
        ),
        concept_criteria=original.concept_criteria,
        additional_file_policy=original.additional_file_policy,
    )


def code_answer_at_size(
    question: CurriculumJavascriptStdinQuestionSnapshot
    | CurriculumReactQuestionSnapshot
    | CurriculumReactFastifyQuestionSnapshot,
    size: int,
) -> CodeAnswer:
    entrypoint = (
        question.frontend_entrypoint
        if isinstance(question, CurriculumReactFastifyQuestionSnapshot)
        else question.entrypoint
    )
    other_files = tuple(
        CodeSubmittedFile(path=item.path, content=item.content)
        for item in question.initial_files
        if item.editable and item.path != entrypoint
    )
    overhead = len(entrypoint.encode('utf-8')) + sum(
        len(item.path.encode('utf-8')) + len(item.content.encode('utf-8'))
        for item in question.initial_files
        if item.path != entrypoint
    )
    content_bytes = size - overhead
    return CodeAnswer(
        question_key=question.key,
        kind=question.kind,
        files=(
            CodeSubmittedFile(
                path=entrypoint,
                content='é' * (content_bytes // 2) + 'x' * (content_bytes % 2),
            ),
            *other_files,
        ),
    )


def _fill(*pairs: tuple[str, str], question_key: str = 'fill-1') -> FillBlanksAnswer:
    return FillBlanksAnswer(
        question_key=question_key,
        placements=tuple(
            FillBlanksPlacement(blank_key=blank, word_key=word) for blank, word in pairs
        ),
    )


class TestPreviewActivityQuestionFeedbackUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.repositories.ordering_passages.find_active.return_value = None
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.provider = create_autospec(CurriculumContentProvider, instance=True)
        self.provider.get_learning_activity.return_value = mixed_snapshot()
        self.assessor = create_autospec(CodeRubricAssessorProvider, instance=True)
        self.assessor.assess.return_value = CodeRubricDecisions(
            criterion_levels=(CodeCriterionDecision(key='correctness', level=75),),
            concept_levels=(),
        )
        self.repositories.goals.find_by_id.return_value = GoalFaker.fake(
            id='goal-1', account_id='account-1'
        )
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = SkillExperienceFaker.fake(
            id='experience-1', goal_id='goal-1', skill_id='skill-1'
        )
        self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value = CompetencyProgress(
            id='progress-1',
            skill_experience_id='experience-1',
            competency_id='competency-1',
            content_released=True,
            created_at=SkillExperienceFaker.fake().created_at,
            updated_at=SkillExperienceFaker.fake().updated_at,
        )
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = None
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_activity_id.return_value = []
        self.translation_assessor = create_autospec(
            TranslationRubricAssessorProvider, instance=True
        )
        self.account_activity_provider = create_autospec(
            AccountActivityProvider, instance=True
        )

        def active_account(_account_id: str) -> AbstractContextManager[None]:
            return nullcontext()

        self.account_activity_provider.activity.side_effect = active_account
        self.account_activity_provider.external_effect.side_effect = (
            _admit_external_effect
        )
        self.subject = PreviewActivityQuestionFeedbackUseCase(
            self.database,
            self.provider,
            self.assessor,
            self.translation_assessor,
            self.account_activity_provider,
        )

    def _execute(
        self, answer: CodeAnswer, revision: str = 'revision-1'
    ) -> PreliminaryQuestionResult:
        return self.subject.execute(
            'account-1',
            'goal-1',
            'skill-1',
            'competency-1',
            'activity-1',
            'q3',
            revision,
            answer,
        )

    @pytest.mark.parametrize('missing', (True, False), ids=('removed', 'revised'))
    def test_should_reject_curriculum_changed_between_projection_and_assessment(
        self, missing: bool
    ) -> None:
        original = mixed_snapshot(react=True)
        self.provider.get_learning_activity.side_effect = (
            original,
            None if missing else replace(original, revision='new-revision'),
        )

        with pytest.raises(ConflictError):
            self._execute(
                CodeAnswer(
                    question_key='q3',
                    kind='react',
                    files=(CodeSubmittedFile(path='src/main.tsx', content='new'),),
                )
            )

        self.assessor.assess.assert_not_called()
        self.repositories.activity_attempts.add.assert_not_called()

    @pytest.mark.parametrize(
        ('question_key', 'answer'),
        (
            (
                'missing',
                ChoiceAnswerSubmission(
                    question_key='missing', selected_option_keys=('a',)
                ),
            ),
            (
                'q1',
                ChoiceAnswerSubmission(question_key='q2', selected_option_keys=('a',)),
            ),
            (
                'q3',
                ChoiceAnswerSubmission(question_key='q3', selected_option_keys=('a',)),
            ),
            (
                'q1',
                CodeAnswer(
                    question_key='q1',
                    files=(CodeSubmittedFile(path='src/main.js', content='new'),),
                ),
            ),
        ),
        ids=(
            'unknown-question',
            'mismatched-key',
            'choice-for-code',
            'code-for-choice',
        ),
    )
    def test_should_reject_answer_not_matching_projected_question_without_effects(
        self, question_key: str, answer: ChoiceAnswerSubmission | CodeAnswer
    ) -> None:
        with pytest.raises(ValidationError):
            self.subject.execute(
                'account-1',
                'goal-1',
                'skill-1',
                'competency-1',
                'activity-1',
                question_key,
                'revision-1',
                answer,
            )

        self.assessor.assess.assert_not_called()
        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.activity_evaluations.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_normalizes_complete_project_and_never_writes(self) -> None:
        result = self._execute(
            CodeAnswer(
                question_key='q3',
                files=(CodeSubmittedFile(path='src/main.js', content='new'),),
            )
        )

        assert result.status == 'conclusive'
        assert result.score == Decimal(75)
        assert result.criteria[0].comment_id == 'level-75'
        request = self.assessor.assess.call_args.args[0]

        assert request.project_files == (
            ('src/lib.js', 'fixed'),
            ('src/main.js', 'new'),
        )
        assert request.submitted_paths == ('src/main.js',)
        self.repositories.activity_attempts.add.assert_not_called()

    @pytest.mark.parametrize(
        'react', (False, True, 'integrated'), ids=('javascript', 'react', 'integrated')
    )
    @pytest.mark.parametrize(
        'limit', (128, 256 * 1024, 512 * 1024), ids=('lower', 'default', 'higher')
    )
    @pytest.mark.parametrize('extra_byte', (0, 1), ids=('exact', 'above'))
    def test_should_apply_configured_utf8_project_limit_before_assessment(
        self, react: bool | str, limit: int, extra_byte: int
    ) -> None:
        snapshot = mixed_snapshot(react=react)
        question = snapshot.questions[-1]
        assert isinstance(
            question,
            (
                CurriculumJavascriptStdinQuestionSnapshot,
                CurriculumReactQuestionSnapshot,
                CurriculumReactFastifyQuestionSnapshot,
            ),
        )
        self.provider.get_learning_activity.return_value = snapshot
        self.subject = PreviewActivityQuestionFeedbackUseCase(
            self.database,
            self.provider,
            self.assessor,
            self.translation_assessor,
            self.account_activity_provider,
            limit,
        )
        answer = code_answer_at_size(question, limit + extra_byte)

        if extra_byte:
            with pytest.raises(ValidationError):
                self._execute(answer)
            self.assessor.assess.assert_not_called()
        else:
            result = self._execute(answer)
            assert result.status == 'conclusive'
            assert result.score == Decimal(75)
            assert {item.path: item.content for item in result.submitted_files}[
                answer.files[0].path
            ] == answer.files[0].content
            self.assessor.assess.assert_called_once()
        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.activity_evaluations.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    @pytest.mark.parametrize('level', (0, 25, 50, 75, 100, 'inconclusive'))
    @pytest.mark.parametrize(
        'source', ('valid', 'syntax error {', 'functionally wrong', 'alternative valid')
    )
    def test_should_assess_integrated_project_without_executing_or_creating_attempt(
        self, level: CodeRubricLevel, source: str
    ) -> None:
        self.provider.get_learning_activity.return_value = mixed_snapshot(
            react='integrated'
        )
        self.assessor.assess.return_value = CodeRubricDecisions(
            criterion_levels=(CodeCriterionDecision(key='correctness', level=level),),
            concept_levels=(),
        )
        answer = CodeAnswer(
            question_key='q3',
            kind='react_fastify',
            files=(
                CodeSubmittedFile(path='src/main.tsx', content=source),
                CodeSubmittedFile(path='routes/api.js', content='saved api'),
                CodeSubmittedFile(path='src/components/Card.tsx', content='additional'),
            ),
        )
        result = self._execute(answer)
        request = self.assessor.assess.call_args.args[0]
        assert request.question_kind == 'react_fastify'
        assert request.project_files == (
            ('routes/api.js', 'saved api'),
            ('src/components/Card.tsx', 'additional'),
            ('src/fixed.css', 'fixed'),
            ('src/main.tsx', source),
        )
        assert request.submitted_paths == (
            'routes/api.js',
            'src/components/Card.tsx',
            'src/main.tsx',
        )
        assert all(
            call.args[0] == 'account-1'
            and isinstance(call.args[1], UUID)
            and call.args[2] == 'learning.code-rubric.assess'
            for call in self.account_activity_provider.external_effect.call_args_list
        )
        assert self.account_activity_provider.external_effect.call_count == 1
        assert result.score == (Decimal(level) if level != 'inconclusive' else None)
        assert result.status == (
            'conclusive' if level != 'inconclusive' else 'inconclusive'
        )
        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.activity_evaluations.add.assert_not_called()
        self.repositories.events.add.assert_not_called()
        if level == 'inconclusive':
            self.assessor.assess.return_value = CodeRubricDecisions(
                criterion_levels=(CodeCriterionDecision(key='correctness', level=75),),
                concept_levels=(),
            )
            recovered = self._execute(answer)
            assert recovered.score == Decimal(75)
            assert (
                self.assessor.assess.call_args_list[0].args[0]
                == self.assessor.assess.call_args_list[1].args[0]
            )

    def test_account_gate_denial_stops_preview_assessment(self) -> None:
        self.account_activity_provider.activity.side_effect = AuthorizationError

        with pytest.raises(AuthorizationError):
            self._execute(
                CodeAnswer(
                    question_key='q3',
                    files=(CodeSubmittedFile(path='src/main.js', content='new'),),
                )
            )

        self.assessor.assess.assert_not_called()
        self.account_activity_provider.external_effect.assert_not_called()

    def test_should_assess_react_initial_and_permitted_additional_files(self) -> None:
        self.provider.get_learning_activity.return_value = mixed_snapshot(react=True)

        result = self._execute(
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
            )
        )

        request = self.assessor.assess.call_args.args[0]
        assert request.question_kind == 'react'
        assert request.project_files == (
            ('src/components/Card.tsx', 'export const Card = () => null'),
            ('src/fixed.css', 'fixed'),
            ('src/main.tsx', 'updated'),
        )
        assert request.submitted_paths == (
            'src/components/Card.tsx',
            'src/main.tsx',
        )
        assert {item.path for item in result.submitted_files} == {
            'src/components/Card.tsx',
            'src/fixed.css',
            'src/main.tsx',
        }

    @pytest.mark.parametrize(
        'additional_path',
        (
            '../escape.tsx',
            'src/components/package.json',
            'src/elsewhere/Card.tsx',
            'src/components/Card.json',
        ),
    )
    def test_should_reject_disallowed_react_additional_file(
        self, additional_path: str
    ) -> None:
        self.provider.get_learning_activity.return_value = mixed_snapshot(react=True)

        with pytest.raises(ValidationError):
            self._execute(
                CodeAnswer(
                    question_key='q3',
                    kind='react',
                    files=(
                        CodeSubmittedFile(path='src/main.tsx', content='updated'),
                        CodeSubmittedFile(path=additional_path, content='extra'),
                    ),
                )
            )

        self.assessor.assess.assert_not_called()
        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.activity_evaluations.add.assert_not_called()
        self.repositories.events.add.assert_not_called()
        self.repositories.competency_progresses.update.assert_not_called()

    def test_should_reject_react_file_count_kind_mismatch_and_oversized_project(
        self,
    ) -> None:
        self.provider.get_learning_activity.return_value = mixed_snapshot(react=True)
        invalid_answers = (
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
                kind='javascript_stdin',
                files=(CodeSubmittedFile(path='src/main.tsx', content='updated'),),
            ),
            CodeAnswer(
                question_key='q3',
                kind='react',
                files=(
                    CodeSubmittedFile(path='src/main.tsx', content='updated'),
                    CodeSubmittedFile(
                        path='src/components/Large.tsx', content='x' * 262144
                    ),
                ),
            ),
        )

        for answer in invalid_answers:
            with pytest.raises(ValidationError):
                self._execute(answer)

        self.assessor.assess.assert_not_called()

    def test_should_reject_additional_file_colliding_with_read_only_initial_file(
        self,
    ) -> None:
        snapshot = mixed_snapshot(react=True)
        question = snapshot.questions[-1]
        assert isinstance(question, CurriculumReactQuestionSnapshot)
        assert question.additional_file_policy is not None
        object.__setattr__(
            question.additional_file_policy, 'allowed_directories', ('src',)
        )
        self.provider.get_learning_activity.return_value = snapshot

        with pytest.raises(ValidationError):
            self._execute(
                CodeAnswer(
                    question_key='q3',
                    kind='react',
                    files=(
                        CodeSubmittedFile(path='src/main.tsx', content='updated'),
                        CodeSubmittedFile(path='src/fixed.css', content='tampered'),
                    ),
                )
            )

        self.assessor.assess.assert_not_called()

    @pytest.mark.parametrize(
        ('answer', 'expected_score', 'expected_explanation'),
        (
            (
                ChoiceAnswerSubmission(question_key='q1', selected_option_keys=('a',)),
                Decimal(100),
                'Correct',
            ),
            (
                ChoiceAnswerSubmission(question_key='q1', selected_option_keys=('b',)),
                Decimal(0),
                'Wrong',
            ),
        ),
    )
    def test_should_return_exact_choice_feedback_without_assessor(
        self,
        answer: ChoiceAnswerSubmission,
        expected_score: Decimal,
        expected_explanation: str,
    ) -> None:
        snapshot = mixed_snapshot()
        question = snapshot.questions[0]
        assert isinstance(question, CurriculumChoiceQuestionSnapshot)
        self.provider.get_learning_activity.return_value = replace(
            snapshot,
            questions=(
                replace(
                    question,
                    options=(
                        *question.options,
                        CurriculumChoiceOptionSnapshot(
                            key='b', text='B', is_correct=False
                        ),
                    ),
                ),
                *snapshot.questions[1:],
            ),
        )

        result = self.subject.execute(
            'account-1',
            'goal-1',
            'skill-1',
            'competency-1',
            'activity-1',
            'q1',
            'revision-1',
            answer,
        )

        assert result.status == 'conclusive'
        assert result.score == expected_score
        assert result.is_correct is (expected_score == 100)
        assert result.explanation == expected_explanation
        assert result.criteria == ()
        assert result.submitted_files == ()
        self.assessor.assess.assert_not_called()

    @pytest.mark.parametrize(
        'answer',
        (
            ChoiceAnswerSubmission(question_key='q1', selected_option_keys=()),
            ChoiceAnswerSubmission(question_key='q1', selected_option_keys=('a', 'a')),
            ChoiceAnswerSubmission(
                question_key='q1', selected_option_keys=('missing',)
            ),
            ChoiceAnswerSubmission(question_key='q1', selected_option_keys=('a', 'b')),
        ),
        ids=('empty', 'duplicate', 'unknown', 'multiple-for-single'),
    )
    def test_should_reject_invalid_choice_feedback_without_assessment(
        self, answer: ChoiceAnswerSubmission
    ) -> None:
        with pytest.raises(ValidationError):
            self.subject.execute(
                'account-1',
                'goal-1',
                'skill-1',
                'competency-1',
                'activity-1',
                'q1',
                'revision-1',
                answer,
            )

        self.assessor.assess.assert_not_called()

    @pytest.mark.parametrize(
        'decisions',
        (
            CodeRubricDecisions(criterion_levels=(), concept_levels=()),
            CodeRubricDecisions(
                criterion_levels=(CodeCriterionDecision(key='other', level=75),),
                concept_levels=(),
            ),
        ),
        ids=('missing-criterion', 'unexpected-criterion'),
    )
    def test_should_reject_invalid_rubric_decisions_without_persistence(
        self, decisions: CodeRubricDecisions
    ) -> None:
        self.assessor.assess.return_value = decisions

        with pytest.raises(ServiceUnavailableError):
            self._execute(
                CodeAnswer(
                    question_key='q3',
                    files=(CodeSubmittedFile(path='src/main.js', content='new'),),
                )
            )

        self.assessor.assess.assert_called_once()
        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.activity_evaluations.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_retries_transient_jev_failure_before_scoring(self) -> None:
        requests: list[httpx.Request] = []

        def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if len(requests) == 1:
                return httpx.Response(503)
            return httpx.Response(
                200,
                json={
                    'answers': {
                        'rubric:correctness': {
                            'type': 'choice',
                            'choice': 'level-75',
                        }
                    }
                },
            )

        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            assessor = JevCodeRubricAssessorProvider(
                api_key='test-key',
                client=client,
                decisions_url='https://openrouter.test/api/alpha/decisions',
                model='typesafe/jev-1.13',
            )
            self.subject = PreviewActivityQuestionFeedbackUseCase(
                self.database,
                self.provider,
                assessor,
                self.translation_assessor,
                self.account_activity_provider,
            )
            result = self._execute(
                CodeAnswer(
                    question_key='q3',
                    files=(CodeSubmittedFile(path='src/main.js', content='new'),),
                )
            )

        assert result.status == 'conclusive'
        assert result.score == Decimal(75)
        assert len(requests) == 2
        assert requests[0].content == requests[1].content

    def test_does_not_retry_nontransient_jev_failure(self) -> None:
        requests: list[httpx.Request] = []

        def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(400)

        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            assessor = JevCodeRubricAssessorProvider(
                api_key='test-key',
                client=client,
                decisions_url='https://openrouter.test/api/alpha/decisions',
                model='typesafe/jev-1.13',
            )
            self.subject = PreviewActivityQuestionFeedbackUseCase(
                self.database,
                self.provider,
                assessor,
                self.translation_assessor,
                self.account_activity_provider,
            )
            with pytest.raises(ServiceUnavailableError):
                self._execute(
                    CodeAnswer(
                        question_key='q3',
                        files=(CodeSubmittedFile(path='src/main.js', content='new'),),
                    )
                )

        assert len(requests) == 1

    def test_exhausted_jev_retries_do_not_produce_a_score(self) -> None:
        requests: list[httpx.Request] = []

        def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(503)

        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            assessor = JevCodeRubricAssessorProvider(
                api_key='test-key',
                client=client,
                decisions_url='https://openrouter.test/api/alpha/decisions',
                model='typesafe/jev-1.13',
            )
            self.subject = PreviewActivityQuestionFeedbackUseCase(
                self.database,
                self.provider,
                assessor,
                self.translation_assessor,
                self.account_activity_provider,
            )
            with pytest.raises(ServiceUnavailableError):
                self._execute(
                    CodeAnswer(
                        question_key='q3',
                        files=(CodeSubmittedFile(path='src/main.js', content='new'),),
                    )
                )

        assert len(requests) == 2
        self.repositories.activity_evaluations.add.assert_not_called()

    def test_rejects_revision_and_missing_or_extra_paths_before_assessor(self) -> None:
        answer = CodeAnswer(
            question_key='q3',
            files=(CodeSubmittedFile(path='src/main.js', content='new'),),
        )
        with pytest.raises(ConflictError):
            self._execute(answer, revision='old')
        with pytest.raises(ValidationError):
            self._execute(CodeAnswer(question_key='q3', files=()))
        with pytest.raises(ValidationError):
            self._execute(
                CodeAnswer(
                    question_key='q3',
                    files=(CodeSubmittedFile(path='src/lib.js', content='bad'),),
                )
            )
        self.assessor.assess.assert_not_called()

    def test_mandatory_inconclusive_has_no_score_and_preserves_source(self) -> None:
        self.assessor.assess.return_value = CodeRubricDecisions(
            criterion_levels=(
                CodeCriterionDecision(key='correctness', level='inconclusive'),
            ),
            concept_levels=(),
        )
        result = self._execute(
            CodeAnswer(
                question_key='q3',
                files=(CodeSubmittedFile(path='src/main.js', content='new'),),
            )
        )

        assert result.status == 'inconclusive'
        assert result.score is None
        assert result.submitted_files[1].content == 'new'

    def test_rejects_large_effective_project_before_assessor(self) -> None:
        self.subject = PreviewActivityQuestionFeedbackUseCase(
            self.database,
            self.provider,
            self.assessor,
            self.translation_assessor,
            self.account_activity_provider,
            2,
        )
        with pytest.raises(ValidationError):
            self._execute(
                CodeAnswer(
                    question_key='q3',
                    files=(CodeSubmittedFile(path='src/main.js', content='new'),),
                )
            )
        self.assessor.assess.assert_not_called()

    def _execute_fill(
        self,
        answer: FillBlanksAnswer | ChoiceAnswerSubmission,
        *,
        question_key: str = 'fill-1',
        revision: str = 'revision-1',
        account_id: str = 'account-1',
        snapshot: CurriculumLearningActivitySnapshot | None = None,
    ) -> PreliminaryQuestionResult:
        self.provider.get_learning_activity.return_value = (
            snapshot or CurriculumFillBlanksActivitySnapshotFaker.fake()
        )
        return self.subject.execute(
            account_id,
            'goal-1',
            'skill-1',
            'competency-1',
            'activity-1',
            question_key,
            revision,
            answer,
        )

    def _assert_nothing_written(self) -> None:
        self.assessor.assess.assert_not_called()
        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.activity_evaluations.add.assert_not_called()
        self.repositories.concept_observations.add_many.assert_not_called()
        self.repositories.events.add.assert_not_called()

    @pytest.mark.parametrize(
        ('pairs', 'score', 'correct_count', 'explanation'),
        (
            (
                (('b1', 'w1'), ('b2', 'w3'), ('b3', 'w4')),
                Decimal('100.00'),
                3,
                'Correct. The third person singular takes -s or -es.',
            ),
            (
                (('b1', 'w2'), ('b2', 'w3'), ('b3', 'w5')),
                Decimal('100.00'),
                3,
                'Correct. The third person singular takes -s or -es.',
            ),
            (
                (('b1', 'w1'), ('b2', 'w3'), ('b3', 'w6')),
                Decimal('66.67'),
                2,
                'Almost there. Review the verb forms.',
            ),
            (
                (('b1', 'w1'), ('b2', 'w6'), ('b3', 'w2')),
                Decimal('33.33'),
                1,
                'Almost there. Review the verb forms.',
            ),
            (
                (('b1', 'w6'), ('b2', 'w2'), ('b3', 'w3')),
                Decimal('0.00'),
                0,
                'Review the third person singular of the present.',
            ),
        ),
        ids=(
            'all-correct',
            'alternative-word-and-repeated-occurrence',
            'two-correct',
            'one-correct',
            'none-correct',
        ),
    )
    def test_should_give_equal_credit_per_blank_without_writing(
        self,
        pairs: tuple[tuple[str, str], ...],
        score: Decimal,
        correct_count: int,
        explanation: str,
    ) -> None:
        result = self._execute_fill(_fill(*pairs))

        assert result.status == 'conclusive'
        assert result.score == score
        assert result.is_correct is (score == 100)
        assert result.explanation == explanation
        assert result.correct_blank_count == correct_count
        assert result.blank_count == 3
        assert result.criteria == ()
        self._assert_nothing_written()

    def test_should_use_the_incorrect_explanation_when_a_single_blank_is_wrong(
        self,
    ) -> None:
        single = CurriculumFillBlanksQuestionSnapshotFaker.fake(
            segments=(CurriculumFillBlanksSegmentSnapshot(blank_key='b1'),),
            blanks=(
                CurriculumFillBlanksBlankSnapshot(key='b1', accepted_words=('goes',)),
            ),
            bank=(
                CurriculumFillBlanksWordSnapshot(key='w1', word='goes'),
                CurriculumFillBlanksWordSnapshot(key='w2', word='go'),
            ),
            concept_criteria=(
                CurriculumFillBlanksConceptCriterionSnapshot(
                    concept_id='c',
                    criterion='x',
                    examples='y',
                    limits='z',
                    blank_keys=('b1',),
                ),
            ),
            partial_explanation=None,
        )
        result = self._execute_fill(
            _fill(('b1', 'w2')),
            snapshot=CurriculumFillBlanksActivitySnapshotFaker.fake(fill_blanks=single),
        )

        assert (result.score, result.correct_blank_count, result.blank_count) == (
            Decimal('0.00'),
            0,
            1,
        )
        assert result.explanation == single.incorrect_explanation

    @pytest.mark.parametrize(
        'answer',
        (
            _fill(('b1', 'w1'), ('b2', 'w3')),
            _fill(('b1', 'w1'), ('b2', 'w1'), ('b3', 'w4')),
            _fill(('b1', 'w1'), ('b2', 'missing'), ('b3', 'w4')),
            _fill(('b1', 'w1'), ('b2', 'w3'), ('unknown', 'w4')),
            _fill(('b1', 'w1'), ('b1', 'w2'), ('b2', 'w3'), ('b3', 'w4')),
            _fill(),
            _fill(('b1', 'w1'), ('b2', 'w3'), ('b3', 'w4'), question_key='q1'),
            ChoiceAnswerSubmission(question_key='fill-1', selected_option_keys=('a',)),
        ),
        ids=(
            'incomplete',
            'repeated-occurrence',
            'unknown-occurrence',
            'unknown-blank',
            'blank-filled-twice',
            'empty',
            'answer-for-another-question',
            'choice-answer-for-fill-blanks',
        ),
    )
    def test_should_reject_an_invalid_fill_without_effects(
        self, answer: FillBlanksAnswer | ChoiceAnswerSubmission
    ) -> None:
        with pytest.raises(ValidationError):
            self._execute_fill(answer)

        self._assert_nothing_written()

    def test_should_reject_a_fill_for_a_choice_question(self) -> None:
        with pytest.raises(ValidationError):
            self._execute_fill(
                _fill(('b1', 'w1'), question_key='q1'), question_key='q1'
            )

        self._assert_nothing_written()

    def test_should_reject_a_stale_revision(self) -> None:
        with pytest.raises(ConflictError):
            self._execute_fill(
                _fill(('b1', 'w1'), ('b2', 'w3'), ('b3', 'w4')), revision='stale'
            )

        self._assert_nothing_written()

    def test_should_reject_another_accounts_experience(self) -> None:
        with pytest.raises(NotFoundError):
            self._execute_fill(
                _fill(('b1', 'w1'), ('b2', 'w3'), ('b3', 'w4')),
                account_id='account-2',
            )

        self._assert_nothing_written()

    def test_should_round_a_tied_percentage_half_up(self) -> None:
        keys = [f'b{number}' for number in range(1, 33)]
        question = CurriculumFillBlanksQuestionSnapshotFaker.fake(
            segments=tuple(
                CurriculumFillBlanksSegmentSnapshot(blank_key=key) for key in keys
            ),
            blanks=tuple(
                CurriculumFillBlanksBlankSnapshot(key=key, accepted_words=('ok',))
                for key in keys
            ),
            bank=(
                *(
                    CurriculumFillBlanksWordSnapshot(key=f'w{number}', word='ok')
                    for number in range(1, 33)
                ),
                *(
                    CurriculumFillBlanksWordSnapshot(key=f'n{number}', word='no')
                    for number in range(2, 33)
                ),
            ),
            concept_criteria=(
                CurriculumFillBlanksConceptCriterionSnapshot(
                    concept_id='c',
                    criterion='x',
                    examples='y',
                    limits='z',
                    blank_keys=tuple(keys),
                ),
            ),
        )
        answer = FillBlanksAnswer(
            question_key=question.key,
            placements=tuple(
                FillBlanksPlacement(
                    blank_key=key, word_key='w1' if number == 1 else f'n{number}'
                )
                for number, key in enumerate(keys, start=1)
            ),
        )

        result = PreviewActivityQuestionFeedbackUseCase.fill_blanks_result(
            question, answer
        )

        assert (result.score, result.correct_blank_count) == (Decimal('3.13'), 1)

    def _translation_criterion(
        self, key: str, weight: int
    ) -> CurriculumTranslationRubricCriterionSnapshot:
        return CurriculumTranslationRubricCriterionSnapshot(
            key=key,
            name=key,
            description=f'Evaluate {key}',
            weight_percentage=weight,
            required=True,
            fixed_comments=tuple(
                CurriculumTranslationRubricCommentSnapshot(
                    id=f'{key}-level-{level}', level=level, text=f'Feedback {level}'
                )
                for level in (0, 25, 50, 75, 100)
            ),
            inconclusive_comment=CurriculumTranslationInconclusiveCommentSnapshot(
                id=f'{key}-unknown', text='Inconclusive'
            ),
        )

    def _use_translation_snapshot(self) -> None:
        filler = tuple(
            CurriculumChoiceQuestionSnapshot(
                key=f'q{number}',
                kind='single_choice',
                prompt='Choose',
                options=(
                    CurriculumChoiceOptionSnapshot(key='a', text='A', is_correct=True),
                ),
                correct_explanation='Correct',
                incorrect_explanation='Wrong',
            )
            for number in (1, 2)
        )
        question = CurriculumTranslationQuestionSnapshot(
            key='qt',
            prompt='Translate',
            source_language='pt-BR',
            target_language='en-US',
            source_text='Bom dia',
            reference_translations=('Good morning',),
            concept_criteria=(),
        )
        part = CurriculumTranslationRubricPartSnapshot(
            question_key='qt',
            weight_percentage=Decimal(40),
            criteria=(
                self._translation_criterion('semantic_preservation', 70),
                self._translation_criterion('grammatical_adequacy', 30),
            ),
        )
        snapshot = CurriculumLearningActivitySnapshot(
            id='activity-1',
            competency_id='competency-1',
            difficulty='easy',
            title='Translation',
            questions=(*filler, question),
            parts=(
                CurriculumChoicePartSnapshot(
                    question_key='q1', weight_percentage=Decimal(30)
                ),
                CurriculumChoicePartSnapshot(
                    question_key='q2', weight_percentage=Decimal(30)
                ),
                part,
            ),
            required_concept_ids=(),
            activity_type='learning',
            schema_version=1,
            revision='revision-1',
        )
        self.provider.get_learning_activity.return_value = snapshot

    def test_should_score_a_conclusive_translation_answer(self) -> None:
        self._use_translation_snapshot()
        self.translation_assessor.assess.return_value = CodeRubricDecisions(
            criterion_levels=(
                CodeCriterionDecision(key='semantic_preservation', level=100),
                CodeCriterionDecision(key='grammatical_adequacy', level=75),
            ),
            concept_levels=(),
        )
        answer = TranslationAnswer(question_key='qt', text='Good morning')

        result = self.subject.execute(
            'account-1',
            'goal-1',
            'skill-1',
            'competency-1',
            'activity-1',
            'qt',
            'revision-1',
            answer,
        )

        assert result.status == 'conclusive'
        assert (
            result.score
            == Decimal(100) * Decimal(70) / 100 + Decimal(75) * Decimal(30) / 100
        )
        assert result.submitted_text == 'Good morning'
        self.repositories.activity_attempts.add.assert_not_called()

    def test_mandatory_inconclusive_translation_criterion_has_no_score(self) -> None:
        self._use_translation_snapshot()
        self.translation_assessor.assess.return_value = CodeRubricDecisions(
            criterion_levels=(
                CodeCriterionDecision(
                    key='semantic_preservation', level='inconclusive'
                ),
                CodeCriterionDecision(key='grammatical_adequacy', level=75),
            ),
            concept_levels=(),
        )
        answer = TranslationAnswer(question_key='qt', text='Good morning')

        result = self.subject.execute(
            'account-1',
            'goal-1',
            'skill-1',
            'competency-1',
            'activity-1',
            'qt',
            'revision-1',
            answer,
        )

        assert result.status == 'inconclusive'
        assert result.score is None
        assert result.submitted_text == 'Good morning'

    def _use_pair_snapshot(self, size: int = 3) -> None:
        base = mixed_snapshot()
        self.provider.get_learning_activity.return_value = replace(
            base,
            questions=(
                base.questions[0],
                base.questions[1],
                CurriculumPairMatchingQuestionSnapshotFaker.fake('qp', size=size),
            ),
            parts=(
                base.parts[0],
                base.parts[1],
                CurriculumChoicePartSnapshot(
                    question_key='qp', weight_percentage=Decimal(40)
                ),
            ),
        )

    @staticmethod
    def _pair_answer(*translation_indexes: int) -> PairMatchingAnswer:
        return PairMatchingAnswer(
            question_key='qp',
            pairs=tuple(
                PairMatchingSelection(
                    word_key=f'word-{word_index}',
                    translation_key=f'translation-{translation_index}',
                )
                for word_index, translation_index in enumerate(translation_indexes)
            ),
        )

    def _execute_pair(
        self, answer: PairMatchingAnswer, revision: str = 'revision-1'
    ) -> PreliminaryQuestionResult:
        return self.subject.execute(
            'account-1',
            'goal-1',
            'skill-1',
            'competency-1',
            'activity-1',
            'qp',
            revision,
            answer,
        )

    @pytest.mark.parametrize('size', (2, 3))
    def test_should_grade_every_permutation_of_a_small_pair_question(
        self, size: int
    ) -> None:
        self._use_pair_snapshot(size)

        for order in permutations(range(size)):
            correct = sum(index == value for index, value in enumerate(order))
            expected_outcome = (
                'full'
                if correct == size
                else 'incorrect'
                if correct == 0
                else 'partial'
            )
            expected_explanation = {
                'full': 'Todos os pares estao corretos.',
                'partial': 'Alguns pares estao corretos.',
                'incorrect': 'Nenhum par esta correto.',
            }[expected_outcome]

            result = self._execute_pair(self._pair_answer(*order))

            assert result.status == 'conclusive'
            assert result.score == _grade(correct, size)
            assert result.correct_pair_count == correct
            assert result.total_pair_count == size
            assert result.outcome == expected_outcome
            assert result.explanation == expected_explanation
            assert result.is_correct is (expected_outcome == 'full')
            assert result.submitted_pairs == self._pair_answer(*order).pairs

    @pytest.mark.parametrize(
        ('order', 'correct'),
        (
            ((0, 1, 2, 3, 4, 5, 6, 7), 8),
            ((1, 2, 3, 4, 5, 6, 7, 0), 0),
            ((1, 0, 2, 3, 4, 5, 6, 7), 6),
            ((0, 1, 2, 3, 4, 5, 7, 6), 6),
            ((7, 1, 2, 3, 4, 5, 6, 0), 6),
        ),
    )
    def test_should_grade_the_largest_pair_question(
        self, order: tuple[int, ...], correct: int
    ) -> None:
        self._use_pair_snapshot(8)

        result = self._execute_pair(self._pair_answer(*order))

        assert result.correct_pair_count == correct
        assert result.total_pair_count == 8
        assert result.score == _grade(correct, 8)

    def test_should_not_create_attempts_or_expose_the_answer_key(self) -> None:
        self._use_pair_snapshot()

        result = self._execute_pair(self._pair_answer(1, 0, 2))

        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.activity_evaluations.add.assert_not_called()
        self.repositories.events.add.assert_not_called()
        self.assessor.assess.assert_not_called()
        self.translation_assessor.assess.assert_not_called()
        assert not hasattr(result, 'correct_pairs')
        assert result.submitted_pairs == self._pair_answer(1, 0, 2).pairs
        assert result.criteria == ()
        assert result.concept_observations == ()

    @pytest.mark.parametrize(
        'order', ((1, 2, 0), (2, 0, 1), (1, 0, 2), (0, 2, 1), (2, 1, 0))
    )
    def test_should_reveal_only_counts_for_wrong_and_partial_answers(
        self, order: tuple[int, ...]
    ) -> None:
        self._use_pair_snapshot()

        result = self._execute_pair(self._pair_answer(*order))

        assert result.outcome in {'partial', 'incorrect'}
        assert {field.name for field in fields(result)} == {
            'status',
            'score',
            'explanation',
            'is_correct',
            'criteria',
            'concept_observations',
            'submitted_files',
            'submitted_text',
            'correct_blank_count',
            'blank_count',
            'submitted_pairs',
            'correct_pair_count',
            'total_pair_count',
            'outcome',
        }

    @pytest.mark.parametrize(
        'answer',
        (
            PairMatchingAnswer(
                question_key='qp',
                pairs=(
                    PairMatchingSelection(
                        word_key='word-0', translation_key='translation-0'
                    ),
                    PairMatchingSelection(
                        word_key='word-1', translation_key='translation-1'
                    ),
                ),
            ),
            PairMatchingAnswer(
                question_key='qp',
                pairs=(
                    PairMatchingSelection(
                        word_key='word-0', translation_key='translation-0'
                    ),
                    PairMatchingSelection(
                        word_key='word-1', translation_key='translation-1'
                    ),
                    PairMatchingSelection(
                        word_key='word-9', translation_key='translation-2'
                    ),
                ),
            ),
            PairMatchingAnswer(
                question_key='qp',
                pairs=(
                    PairMatchingSelection(
                        word_key='word-0', translation_key='translation-0'
                    ),
                    PairMatchingSelection(
                        word_key='word-1', translation_key='translation-1'
                    ),
                    PairMatchingSelection(
                        word_key='word-2', translation_key='translation-9'
                    ),
                ),
            ),
            PairMatchingAnswer(
                question_key='other',
                pairs=(
                    PairMatchingSelection(
                        word_key='word-0', translation_key='translation-0'
                    ),
                    PairMatchingSelection(
                        word_key='word-1', translation_key='translation-1'
                    ),
                    PairMatchingSelection(
                        word_key='word-2', translation_key='translation-2'
                    ),
                ),
            ),
            ChoiceAnswerSubmission(question_key='qp', selected_option_keys=('a',)),
        ),
        ids=(
            'missing-pair',
            'unknown-word',
            'unknown-translation',
            'wrong-question-key',
            'wrong-answer-type',
        ),
    )
    def test_should_reject_invalid_pair_answers_without_writes(
        self, answer: PairMatchingAnswer | ChoiceAnswerSubmission
    ) -> None:
        self._use_pair_snapshot()

        with pytest.raises(ValidationError):
            self.subject.execute(
                'account-1',
                'goal-1',
                'skill-1',
                'competency-1',
                'activity-1',
                'qp',
                'revision-1',
                answer,  # type: ignore[arg-type]
            )

        self.repositories.activity_attempts.add.assert_not_called()

    def test_should_reject_repeated_words_and_translations_in_the_answer(
        self,
    ) -> None:
        with pytest.raises(ValidationError):
            PairMatchingAnswer(
                question_key='qp',
                pairs=(
                    PairMatchingSelection(
                        word_key='word-0', translation_key='translation-0'
                    ),
                    PairMatchingSelection(
                        word_key='word-0', translation_key='translation-1'
                    ),
                ),
            )
        with pytest.raises(ValidationError):
            PairMatchingAnswer(
                question_key='qp',
                pairs=(
                    PairMatchingSelection(
                        word_key='word-0', translation_key='translation-0'
                    ),
                    PairMatchingSelection(
                        word_key='word-1', translation_key='translation-0'
                    ),
                ),
            )

    def test_should_reject_a_stale_activity_revision_for_pair_feedback(
        self,
    ) -> None:
        self._use_pair_snapshot()

        with pytest.raises(ConflictError):
            self._execute_pair(self._pair_answer(0, 1, 2), revision='old-revision')

        self.repositories.activity_attempts.add.assert_not_called()

    @pytest.mark.parametrize(
        'case',
        (
            'too-few-pairs',
            'too-many-pairs',
            'repeated-word-key',
            'repeated-translation-text',
            'key-skips-a-word',
            'key-uses-unknown-translation',
            'key-order-aligned-with-display',
        ),
    )
    def test_should_reject_an_invalid_pair_matching_snapshot(self, case: str) -> None:
        question = CurriculumPairMatchingQuestionSnapshotFaker.fake('qp', size=3)
        words, translations, pairs = (
            question.words,
            question.translations,
            question.correct_pairs,
        )
        changes: dict[str, dict[str, Any]] = {
            'too-few-pairs': {
                'words': words[:1],
                'translations': translations[:1],
                'correct_pairs': pairs[:1],
            },
            'too-many-pairs': {
                'words': tuple(
                    CurriculumPairMatchingItemSnapshot(key=f'w{i}', text=f'w{i}')
                    for i in range(9)
                ),
                'translations': tuple(
                    CurriculumPairMatchingItemSnapshot(key=f't{i}', text=f't{i}')
                    for i in range(9)
                ),
                'correct_pairs': tuple(
                    CurriculumPairMatchingPairSnapshot(
                        word_key=f'w{i}', translation_key=f't{(i + 1) % 9}'
                    )
                    for i in range(9)
                ),
            },
            'repeated-word-key': {
                'words': (words[0], replace(words[1], key=words[0].key), words[2])
            },
            'repeated-translation-text': {
                'translations': (
                    translations[0],
                    replace(translations[1], text=translations[0].text),
                    translations[2],
                )
            },
            'key-skips-a-word': {
                'correct_pairs': (pairs[0], pairs[0], pairs[2]),
            },
            'key-uses-unknown-translation': {
                'correct_pairs': (
                    pairs[0],
                    pairs[1],
                    CurriculumPairMatchingPairSnapshot(
                        word_key=pairs[2].word_key, translation_key='missing'
                    ),
                ),
            },
            'key-order-aligned-with-display': {
                'translations': tuple(sorted(translations, key=lambda item: item.key)),
            },
        }

        with pytest.raises(ValidationError):
            replace(question, **changes[case])

    @pytest.mark.parametrize('catalog_present', (True, False))
    def test_should_preview_translation_from_pinned_ordering_passage_after_catalog_change(
        self, catalog_present: bool
    ) -> None:
        self._use_translation_snapshot()
        snapshot = self.provider.get_learning_activity.return_value
        assert isinstance(snapshot, CurriculumLearningActivitySnapshot)
        ordering = CurriculumOrderingQuestionSnapshot(
            key='q2',
            kind='ordering',
            prompt='Order the steps',
            steps=tuple(
                CurriculumOrderingStepSnapshot(key=key, text=key)
                for key in ('prepare', 'cook', 'serve')
            ),
            accepted_orders=(('prepare', 'cook', 'serve'),),
            correct_explanation='Correct',
            incorrect_explanation='Wrong',
            concept_criteria=(
                CurriculumChoiceConceptCriterionSnapshot(
                    concept_id='concept-order',
                    criterion='Orders steps',
                    examples='Prepare first',
                    limits='No practical execution',
                    correct_score=Decimal(100),
                    incorrect_score=Decimal(0),
                ),
            ),
        )
        pinned = replace(
            snapshot, questions=(snapshot.questions[0], ordering, snapshot.questions[2])
        )
        passage = OrderingPassage.create(
            id='passage-1',
            skill_experience_id='experience-1',
            activity_id='activity-1',
            passage_key='passage-key',
            activity_revision='revision-1',
            grading_snapshot=pinned,
        )
        passage.add_verified(
            VerifiedOrdering(
                question_key='q2',
                ordered_step_keys=('prepare', 'cook', 'serve'),
                score=Decimal(100),
                is_correct=True,
                explanation='Correct',
            )
        )
        self.repositories.ordering_passages.find_active.return_value = passage
        self.provider.get_learning_activity.return_value = (
            replace(snapshot, revision='revision-2') if catalog_present else None
        )
        self.translation_assessor.assess.return_value = CodeRubricDecisions(
            criterion_levels=(
                CodeCriterionDecision(key='semantic_preservation', level=100),
                CodeCriterionDecision(key='grammatical_adequacy', level=100),
            ),
            concept_levels=(),
        )

        result = self.subject.execute(
            'account-1',
            'goal-1',
            'skill-1',
            'competency-1',
            'activity-1',
            'qt',
            'revision-1',
            TranslationAnswer(question_key='qt', text='Good morning'),
        )

        assert result.status == 'conclusive'
        assert result.score == Decimal(100)
        assert result.submitted_text == 'Good morning'
        self.provider.get_learning_activity.assert_not_called()
        request = self.translation_assessor.assess.call_args.args[0]
        assert request.reference_translations == ('Good morning',)
        assert request.submitted_text == 'Good morning'
        assert passage.status == 'active'
        assert len(passage.verified_orderings) == 1
        self.repositories.activity_attempts.add.assert_not_called()


class TestPreviewOrderingQuestion:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.provider = create_autospec(CurriculumContentProvider, instance=True)
        self.account_activity_provider = create_autospec(
            AccountActivityProvider, instance=True
        )
        def activity_scope(_account_id: str) -> AbstractContextManager[None]:
            return nullcontext()

        self.account_activity_provider.activity.side_effect = activity_scope
        base = mixed_snapshot()
        self.snapshot = replace(
            base,
            questions=(
                *base.questions[:2],
                CurriculumOrderingQuestionSnapshot(
                    key='q3',
                    kind='ordering',
                    prompt='Organize as etapas.',
                    steps=tuple(
                        CurriculumOrderingStepSnapshot(key=key, text=text)
                        for key, text in (
                            ('prepare', 'Preparar'),
                            ('cook', 'Cozinhar'),
                            ('serve', 'Servir'),
                        )
                    ),
                    accepted_orders=(
                        ('prepare', 'cook', 'serve'),
                        ('prepare', 'serve', 'cook'),
                    ),
                    correct_explanation='Sequência aceita.',
                    incorrect_explanation='Revise a sequência.',
                    concept_criteria=(
                        CurriculumChoiceConceptCriterionSnapshot(
                            concept_id='concept-order',
                            criterion='Ordem do processo',
                            examples='Preparar antes de cozinhar.',
                            limits='A apresentação pode variar.',
                            correct_score=Decimal(100),
                            incorrect_score=Decimal(0),
                        ),
                    ),
                ),
            ),
            parts=tuple(
                CurriculumChoicePartSnapshot(
                    question_key=f'q{index}', weight_percentage=Decimal(weight)
                )
                for index, weight in ((1, 30), (2, 30), (3, 40))
            ),
        )
        self.provider.get_learning_activity.return_value = self.snapshot
        self.assessor = create_autospec(CodeRubricAssessorProvider, instance=True)
        self.identifiers = create_autospec(IdentifierProvider, instance=True)
        self.identifiers.generate.return_value = '01JSHIFU129ORDERINGPASS'
        self.repositories.goals.find_by_id.return_value = GoalFaker.fake(
            id='goal-1', account_id='account-1'
        )
        experience = SkillExperienceFaker.fake(
            id='experience-1',
            goal_id='goal-1',
            skill_id='skill-1',
            status=SkillExperienceStatus.LEARNING,
        )
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = experience
        self.repositories.skill_experiences.find_by_id_for_update.return_value = (
            experience
        )
        self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value = CompetencyProgress(
            id='progress-1',
            skill_experience_id='experience-1',
            competency_id='competency-1',
            content_released=True,
            created_at=experience.created_at,
            updated_at=experience.updated_at,
        )
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = None
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_activity_id.return_value = []
        self.passages: list[OrderingPassage] = []

        def find_active(
            _skill_experience_id: str,
            _activity_id: str,
        ) -> OrderingPassage | None:
            return self.passages[0] if self.passages else None

        def find_by_key(
            _skill_experience_id: str,
            _activity_id: str,
            _passage_key: str,
        ) -> OrderingPassage | None:
            return self.passages[0] if self.passages else None

        def add_passage(passage: OrderingPassage) -> None:
            self.passages.append(passage)

        def update_passage(_passage: OrderingPassage) -> None:
            return None

        self.repositories.ordering_passages.find_active.side_effect = find_active
        self.repositories.ordering_passages.find_by_key.side_effect = find_by_key
        self.repositories.ordering_passages.add.side_effect = add_passage
        self.repositories.ordering_passages.update.side_effect = update_passage
        self.subject = PreviewActivityQuestionFeedbackUseCase(
            self.database,
            self.provider,
            self.assessor,
            translation_rubric_assessor_provider=create_autospec(
                TranslationRubricAssessorProvider, instance=True
            ),
            account_activity_provider=self.account_activity_provider,
            identifier_provider=self.identifiers,
        )

    def _verify(self, ordered: tuple[str, ...]) -> PreliminaryQuestionResult:
        from shifu.learning.core.domain.structures import OrderingAnswerSubmission

        return self.subject.execute(
            'account-1',
            'goal-1',
            'skill-1',
            'competency-1',
            'activity-1',
            'q3',
            'revision-1',
            OrderingAnswerSubmission(question_key='q3', ordered_step_keys=ordered),
            'passage-uuid',
        )

    def test_should_persist_verified_order_and_replay_immutable_result(self) -> None:
        first = self._verify(('prepare', 'cook', 'serve'))
        replay = self._verify(('prepare', 'cook', 'serve'))

        assert first == replay
        assert first.score == Decimal(100)
        assert first.is_correct is True
        assert first.explanation == 'Sequência aceita.'
        assert len(self.passages) == 1
        assert len(self.passages[0].verified_orderings) == 1
        self.repositories.ordering_passages.update.assert_not_called()
        self.repositories.activity_attempts.add.assert_not_called()

    def test_should_reject_different_order_after_first_verification(self) -> None:
        self._verify(('prepare', 'cook', 'serve'))

        with pytest.raises(ConflictError):
            self._verify(('cook', 'prepare', 'serve'))

        assert len(self.passages[0].verified_orderings) == 1
        self.repositories.ordering_passages.update.assert_not_called()

    def test_should_reject_route_and_ordering_question_key_mismatch(self) -> None:
        from shifu.learning.core.domain.structures import OrderingAnswerSubmission

        with pytest.raises(ValidationError):
            self.subject.execute(
                'account-1',
                'goal-1',
                'skill-1',
                'competency-1',
                'activity-1',
                'q1',
                'revision-1',
                OrderingAnswerSubmission(
                    question_key='q3',
                    ordered_step_keys=('prepare', 'cook', 'serve'),
                ),
                'passage-uuid',
            )

        assert not self.passages
        self.repositories.ordering_passages.add.assert_not_called()

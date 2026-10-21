from dataclasses import replace
from decimal import Decimal
from unittest.mock import create_autospec

import httpx
import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.intelligence.providers.code_rubric_assessor_provider.jev_code_rubric_assessor_provider import (
    JevCodeRubricAssessorProvider,
)
from shifu.learning.core.domain.entities import CompetencyProgress
from shifu.learning.core.domain.structures import (
    ChoiceAnswerSubmission,
    CodeAnswer,
    CodeSubmittedFile,
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
    ConflictError,
    ServiceUnavailableError,
    ValidationError,
)
from shifu.shared.core.domain.structures import (
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
    CurriculumLearningActivitySnapshot,
)
from shifu.shared.core.interfaces import (
    CodeRubricAssessorProvider,
    CurriculumContentProvider,
)


def mixed_snapshot(*, react: bool = False) -> CurriculumLearningActivitySnapshot:
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


def code_answer_at_size(
    question: CurriculumJavascriptStdinQuestionSnapshot
    | CurriculumReactQuestionSnapshot,
    size: int,
) -> CodeAnswer:
    overhead = len(question.entrypoint.encode('utf-8')) + sum(
        len(item.path.encode('utf-8')) + len(item.content.encode('utf-8'))
        for item in question.initial_files
        if not item.editable
    )
    content_bytes = size - overhead
    return CodeAnswer(
        question_key=question.key,
        kind=question.kind,
        files=(
            CodeSubmittedFile(
                path=question.entrypoint,
                content='é' * (content_bytes // 2) + 'x' * (content_bytes % 2),
            ),
        ),
    )


class TestPreviewActivityQuestionFeedbackUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
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
        self.subject = PreviewActivityQuestionFeedbackUseCase(
            self.database, self.provider, self.assessor
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

    @pytest.mark.parametrize('react', (False, True), ids=('javascript', 'react'))
    @pytest.mark.parametrize(
        'limit', (128, 256 * 1024, 512 * 1024), ids=('lower', 'default', 'higher')
    )
    @pytest.mark.parametrize('extra_byte', (0, 1), ids=('exact', 'above'))
    def test_should_apply_configured_utf8_project_limit_before_assessment(
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
        self.subject = PreviewActivityQuestionFeedbackUseCase(
            self.database, self.provider, self.assessor, limit
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
            assert result.submitted_files[-1].content == answer.files[0].content
            self.assessor.assess.assert_called_once()
        self.repositories.activity_attempts.add.assert_not_called()
        self.repositories.activity_evaluations.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

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
                self.database, self.provider, assessor
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
                self.database, self.provider, assessor
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
                self.database, self.provider, assessor
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
            self.database, self.provider, self.assessor, 2
        )
        with pytest.raises(ValidationError):
            self._execute(
                CodeAnswer(
                    question_key='q3',
                    files=(CodeSubmittedFile(path='src/main.js', content='new'),),
                )
            )
        self.assessor.assess.assert_not_called()

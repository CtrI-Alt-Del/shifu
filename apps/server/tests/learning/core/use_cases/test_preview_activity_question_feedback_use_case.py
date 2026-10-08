from decimal import Decimal
from unittest.mock import create_autospec

import httpx
import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.intelligence.providers.code_rubric_assessor_provider.jev_code_rubric_assessor_provider import (
    JevCodeRubricAssessorProvider,
)
from shifu.learning.core.domain.entities import CompetencyProgress
from shifu.learning.core.domain.structures import CodeAnswer, CodeSubmittedFile
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
    CurriculumLearningActivitySnapshot,
)
from shifu.shared.core.interfaces import (
    CodeRubricAssessorProvider,
    CurriculumContentProvider,
)


def mixed_snapshot() -> CurriculumLearningActivitySnapshot:
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
    code = CurriculumJavascriptStdinQuestionSnapshot(
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
        self.repositories.activity_evaluations.add.assert_not_called()
        self.repositories.events.add.assert_not_called()
        self.repositories.competency_progresses.update.assert_not_called()

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

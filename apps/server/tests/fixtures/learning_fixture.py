"""Learning test support: a seeded code activity attempt bound to the disposable
PostgreSQL database, for workflow tests that grade it in process."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from shifu.curriculum.core.domain.entities import Activity, Concept
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    ActivitySequenceItem,
    ChoiceConceptCriterion,
    ChoiceOption,
    CodeInconclusiveComment,
    CodeRubricComment,
    CodeRubricCriterion,
    CodeRubricEvaluationPart,
    CorrectnessEvaluationPart,
    CurriculumSequence,
    EvaluationRule,
    JavascriptInitialFile,
    JavascriptStdinQuestion,
    SingleChoiceQuestion,
)
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers.curriculum_content_provider import (
    DatabaseCurriculumContentProvider,
)
from shifu.fakers.curriculum.entities import CompetencyFaker, SkillFaker
from shifu.fakers.identity.entities import AccountFaker
from shifu.fakers.learning.entities import (
    CompetencyProgressFaker,
    GoalFaker,
    SkillExperienceFaker,
)
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.learning.core.domain.entities import ActivityAttempt, ActivityEvaluation
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures import (
    CodeAnswer,
    CodeSubmittedFile,
    SingleChoiceAnswer,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

CODE_QUESTION_KEY = 'q3'
CODE_CRITERION_KEY = 'correctness'


@dataclass(frozen=True)
class SeededCodeActivity:
    """One mixed activity (two choice questions, one code question) with a
    pending evaluation of a submitted attempt."""

    database: SqlalchemyLearningDatabase
    content_provider: DatabaseCurriculumContentProvider
    attempt: ActivityAttempt
    evaluation: ActivityEvaluation

    @property
    def run_id(self) -> str:
        assert self.evaluation.run_id is not None
        return self.evaluation.run_id

    def current_evaluation(self) -> ActivityEvaluation:
        with self.database.transaction() as repositories:
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                self.attempt.id
            )
        assert evaluation is not None
        return evaluation


def seed_code_activity_attempt(
    engine: Engine, *, source_code: str = 'console.log(42)'
) -> SeededCodeActivity:
    ids = SystemIdentifierProvider()
    now = SystemClockProvider().now()
    account = AccountFaker.fake(created_at=now)
    skill = SkillFaker.fake()
    competency = CompetencyFaker.fake(skill_id=skill.id)
    concept = Concept(
        id=ids.generate(),
        competency_id=competency.id,
        name='Code evaluation concept',
        description='A concept used by the learning workflow fixture.',
        position=1,
        observation_criteria='Observe whether the learner identifies the rule.',
    )
    choice_questions = tuple(
        SingleChoiceQuestion(
            key=f'q{number}',
            prompt=f'Pergunta {number}?',
            options=(
                ChoiceOption(key='correct', text='Correta', is_correct=True),
                ChoiceOption(key='incorrect', text='Incorreta', is_correct=False),
            ),
            correct_explanation='Correta',
            incorrect_explanation='Incorreta',
            concept_criteria=(
                ChoiceConceptCriterion(
                    concept_id=concept.id,
                    criterion='Identifies the concept rule.',
                    examples='Expected answer',
                    limits='The answer provides limited evidence.',
                    correct_score=100,
                    incorrect_score=0,
                ),
            ),
        )
        for number in (1, 2)
    )
    code_question = JavascriptStdinQuestion(
        key=CODE_QUESTION_KEY,
        prompt='Leia stdin e produza a saída esperada.',
        initial_files=(
            JavascriptInitialFile(
                path='src/main.js', content='console.log(0)', editable=True
            ),
        ),
        entrypoint='src/main.js',
        fixed_dependencies=(),
        permitted_commands=(),
        concept_criteria=(),
    )
    criterion = CodeRubricCriterion(
        key=CODE_CRITERION_KEY,
        name='Correção',
        description='A saída corresponde à especificação.',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CodeRubricComment(
                id=f'comment-{level}', level=level, text=f'Comment {level}'
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CodeInconclusiveComment(
            id='comment-inconclusive', text='Inconclusivo'
        ),
    )
    activity = Activity.create(
        id=ids.generate(),
        competency_id=competency.id,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.EASY,
        title='Atividade mista do workflow',
        objective='Avaliar escolha e código.',
        questions=(*choice_questions, code_question),
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(question_key='q1', weight_percentage=30),
                CorrectnessEvaluationPart(question_key='q2', weight_percentage=30),
                CodeRubricEvaluationPart(
                    question_key=CODE_QUESTION_KEY,
                    weight_percentage=40,
                    criteria=(criterion,),
                ),
            )
        ),
    )
    goal = GoalFaker.fake(account_id=account.id, created_at=now, updated_at=now)
    experience = SkillExperienceFaker.fake(
        goal_id=goal.id,
        skill_id=skill.id,
        status=SkillExperienceStatus.LEARNING,
        created_at=now,
        updated_at=now,
    )
    progress = CompetencyProgressFaker.fake(
        skill_experience_id=experience.id,
        competency_id=competency.id,
        content_released=True,
        initial_progress=Decimal('0'),
        current_progress=Decimal('0'),
        status=CompetencyProgressStatus.LEARNING,
        created_at=now,
        updated_at=now,
    )
    with SqlalchemyIdentityDatabase(engine, id_provider=ids).transaction() as repos:
        repos.accounts.add(account)
    curriculum_database = SqlalchemyCurriculumDatabase(engine)
    with curriculum_database.transaction() as repos:
        repos.skills.add_many([skill])
        repos.competencies.add_many([competency])
        repos.activities.add_many([activity])
        repos.concepts.add_many([concept])
        repos.curriculum_sequences.add_many(
            [
                CurriculumSequence(
                    competency_id=competency.id,
                    items=(ActivitySequenceItem(activity_id=activity.id, position=1),),
                )
            ]
        )
    database = SqlalchemyLearningDatabase(engine, id_provider=ids)
    with database.transaction() as repos:
        repos.goals.add(goal)
        repos.skill_experiences.add_many([experience])
        repos.competency_progresses.add(progress)
    provider = DatabaseCurriculumContentProvider(
        curriculum_database,
        diagnostic_revision_hmac_key=b'workflow-test-diagnostic-revision-key',
    )
    snapshot = provider.get_learning_activity(activity.id)
    assert snapshot is not None
    attempt = ActivityAttempt.create(
        id=ids.generate(),
        skill_experience_id=experience.id,
        competency_id=activity.competency_id,
        activity_id=activity.id,
        kind=ActivityAttemptKind.LEARNING,
        answers=(
            SingleChoiceAnswer(question_key='q1', selected_option_key='correct'),
            SingleChoiceAnswer(question_key='q2', selected_option_key='correct'),
            CodeAnswer(
                question_key=CODE_QUESTION_KEY,
                files=(CodeSubmittedFile(path='src/main.js', content=source_code),),
            ),
        ),
        submitted_at=now,
        submission_key=ids.generate(),
        grading_snapshot=snapshot,
    )
    evaluation = ActivityEvaluation.create(
        id=ids.generate(),
        attempt_id=attempt.id,
        status=ActivityEvaluationStatus.PENDING,
        parts=(),
        started_at=now,
        run_id=ids.generate(),
    )
    with database.transaction() as repos:
        repos.activity_attempts.add(attempt)
        repos.activity_evaluations.add(evaluation)
    return SeededCodeActivity(database, provider, attempt, evaluation)

from unittest.mock import create_autospec
import pytest
from shifu.intelligence.core.domain.enums import (
    PlanningOperationKind,
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.errors import (
    PlanningAnswersInvalidError,
    PlanningOperationConflictError,
    PlanningSessionNotFoundError,
)
from shifu.intelligence.core.domain.events import (
    PlanningOperationRequestedEvent,
    PlanningOperationRequestedPayload,
)
from shifu.intelligence.core.domain.structures import PlanningAnswer
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    PlanningSessionsRepository,
)
from shifu.intelligence.core.use_cases import AnswerPlanningQuestionsUseCase
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider
from tests.intelligence.core.use_cases.planning_test_setup import (
    ACCOUNT_ID,
    NEXT_OPERATION_ID,
    NOW,
    OTHER_ACCOUNT_ID,
    PLANNING_ID,
    interviewing_session,
    started_session,
)
from datetime import timedelta
from shifu.intelligence.core.domain.enums import PlanningQuestionKind
from shifu.intelligence.core.domain.errors import PlanningStateConflictError
from shifu.intelligence.core.domain.structures import (
    PlanningOperationResult,
)
from tests.fixtures.curriculum_planning_boundary_fixture import (
    BOUNDARY_NOW,
    BOUNDARY_OPERATION_ID,
    BOUNDARY_NEXT_OPERATION_ID,
    boundary_question,
    boundary_batch,
    boundary_proposal,
    boundary_session,
    boundary_interviewing,
    boundary_complete,
    boundary_answer,
    boundary_restart,
    boundary_retry,
)


_VALID = (PlanningAnswer(question_id='q1', option_ids=('o2',)),)


class TestAnswerPlanningQuestionsUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.sessions = create_autospec(PlanningSessionsRepository, instance=True)
        self.sessions.update.return_value = True
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.identifiers = create_autospec(IdentifierProvider, instance=True)
        self.identifiers.generate.return_value = NEXT_OPERATION_ID
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.use_case = AnswerPlanningQuestionsUseCase(
            self.sessions, self.database, self.identifiers, self.clock
        )

    def test_should_record_the_batch_and_request_the_next_operation(self) -> None:
        session = interviewing_session()
        self.sessions.find_by_id.return_value = session

        result = self.use_case.execute(ACCOUNT_ID, PLANNING_ID, 'batch-1', _VALID)

        assert result is session
        assert result.status is PlanningSessionStatus.PROCESSING
        assert result.operation is not None
        assert result.operation.id == NEXT_OPERATION_ID
        assert result.operation.kind is PlanningOperationKind.ANSWER
        assert result.batch is None
        assert result.answered_batch_count == 1
        self.sessions.update.assert_called_once_with(session)
        self.repositories.events.add.assert_called_once_with(
            PlanningOperationRequestedEvent(
                payload=PlanningOperationRequestedPayload(
                    planning_id=PLANNING_ID,
                    operation_id=NEXT_OPERATION_ID,
                    generation=1,
                )
            )
        )

    @pytest.mark.parametrize(
        'answers',
        [
            (),
            (PlanningAnswer(question_id='q1', option_ids=('o9',)),),
            (PlanningAnswer(question_id='q1', option_ids=('nao-sei', 'o1')),),
        ],
    )
    def test_should_reject_invalid_answers_without_any_write(
        self, answers: tuple[PlanningAnswer, ...]
    ) -> None:
        self.sessions.find_by_id.return_value = interviewing_session()

        with pytest.raises(PlanningAnswersInvalidError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID, 'batch-1', answers)

        self.sessions.update.assert_not_called()
        self.database.transaction.assert_not_called()

    def test_should_refuse_answers_while_an_operation_is_running(self) -> None:
        self.sessions.find_by_id.return_value = started_session()

        with pytest.raises(PlanningOperationConflictError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID, 'batch-1', _VALID)

        self.sessions.update.assert_not_called()
        self.database.transaction.assert_not_called()

    def test_should_refuse_the_submission_that_loses_the_concurrent_write(
        self,
    ) -> None:
        self.sessions.find_by_id.return_value = interviewing_session()
        self.sessions.update.return_value = False

        with pytest.raises(PlanningOperationConflictError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID, 'batch-1', _VALID)

        self.database.transaction.assert_not_called()

    def test_should_hide_a_foreign_planning(self) -> None:
        self.sessions.find_by_id.return_value = interviewing_session(OTHER_ACCOUNT_ID)

        with pytest.raises(PlanningSessionNotFoundError):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID, 'batch-1', _VALID)

        self.sessions.update.assert_not_called()


class TestAnswerPlanningQuestionsMigratedTransitions:
    def test_should_expose_a_batch_and_accept_a_complete_valid_answer_set(self) -> None:
        session = boundary_interviewing()
        later = BOUNDARY_NOW + timedelta(minutes=1)
        assert session.status is PlanningSessionStatus.INTERVIEW
        assert session.batch is not None
        boundary_answer(
            session,
            'batch-1',
            (PlanningAnswer(question_id='q1', option_ids=('o2',)),),
            BOUNDARY_NEXT_OPERATION_ID,
            later,
        )
        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.operation is not None
        assert session.operation.kind is PlanningOperationKind.ANSWER
        assert session.operation.id == BOUNDARY_NEXT_OPERATION_ID
        assert session.batch is None
        assert session.answered_batch_count == 1
        assert session.answered_batches[0].items[0].selected_texts == ('APIs',)
        assert session.updated_at == later

    @pytest.mark.parametrize(
        ('batch_id', 'answers', 'error'),
        [
            (
                'batch-2',
                (PlanningAnswer(question_id='q1', option_ids=('o1',)),),
                PlanningStateConflictError,
            ),
            ('batch-1', (), PlanningAnswersInvalidError),
            (
                'batch-1',
                (PlanningAnswer(question_id='q9', option_ids=('o1',)),),
                PlanningAnswersInvalidError,
            ),
            (
                'batch-1',
                (PlanningAnswer(question_id='q1', option_ids=('o9',)),),
                PlanningAnswersInvalidError,
            ),
            (
                'batch-1',
                (PlanningAnswer(question_id='q1', option_ids=('o1', 'o2')),),
                PlanningAnswersInvalidError,
            ),
            (
                'batch-1',
                (PlanningAnswer(question_id='q1', option_ids=()),),
                PlanningAnswersInvalidError,
            ),
            (
                'batch-1',
                (
                    PlanningAnswer(question_id='q1', option_ids=('o1',)),
                    PlanningAnswer(question_id='q1', option_ids=('o2',)),
                ),
                PlanningAnswersInvalidError,
            ),
        ],
    )
    def test_should_reject_incomplete_or_invalid_answer_sets_without_changing_state(
        self, batch_id: str, answers: tuple[PlanningAnswer, ...], error: type[Exception]
    ) -> None:
        session = boundary_interviewing()
        with pytest.raises(error):
            boundary_answer(
                session, batch_id, answers, BOUNDARY_NEXT_OPERATION_ID, BOUNDARY_NOW
            )
        assert session.status is PlanningSessionStatus.INTERVIEW
        assert session.operation is None
        assert session.answered_batch_count == 0

    def test_should_keep_the_unknown_option_exclusive_on_multiple_choice(self) -> None:
        question = boundary_question(kind=PlanningQuestionKind.MULTIPLE, unknown=True)
        session = boundary_session()
        assert boundary_complete(
            session,
            BOUNDARY_OPERATION_ID,
            1,
            PlanningOperationResult.for_batch(boundary_batch(question)),
            BOUNDARY_NOW,
        )
        with pytest.raises(PlanningAnswersInvalidError, match='Não sei'):
            boundary_answer(
                session,
                'batch-1',
                (PlanningAnswer(question_id='q1', option_ids=('nao-sei', 'o1')),),
                BOUNDARY_NEXT_OPERATION_ID,
                BOUNDARY_NOW,
            )
        boundary_answer(
            session,
            'batch-1',
            (PlanningAnswer(question_id='q1', option_ids=('o1', 'o2')),),
            BOUNDARY_NEXT_OPERATION_ID,
            BOUNDARY_NOW,
        )
        assert session.answered_batches[0].items[0].selected_texts == ('Sites', 'APIs')

    def test_should_combine_other_with_alternatives_and_keep_the_learner_text(
        self,
    ) -> None:
        question = boundary_question(
            kind=PlanningQuestionKind.MULTIPLE, unknown=True, other=True
        )
        session = boundary_session()
        assert boundary_complete(
            session,
            BOUNDARY_OPERATION_ID,
            1,
            PlanningOperationResult.for_batch(boundary_batch(question)),
            BOUNDARY_NOW,
        )
        boundary_answer(
            session,
            'batch-1',
            (
                PlanningAnswer(
                    question_id='q1',
                    option_ids=('o1', 'outro'),
                    other_text='  planilhas   no Excel ',
                ),
            ),
            BOUNDARY_NEXT_OPERATION_ID,
            BOUNDARY_NOW,
        )
        item = session.answered_batches[0].items[0]
        assert item.other_text == 'planilhas no Excel'
        assert item.selected_texts == ('Sites',)
        assert item.answer_texts == ('Sites', 'planilhas no Excel')

    @pytest.mark.parametrize(
        ('option_ids', 'other_text', 'message'),
        [
            (('outro',), None, 'Descreva'),
            (('outro',), '   ', 'Descreva'),
            (('outro',), 'x' * 201, '200 caracteres'),
            (('o1',), 'planilhas', 'exige a alternativa'),
            (('outro', 'nao-sei'), 'planilhas', 'Não sei'),
        ],
    )
    def test_should_reject_an_invalid_open_answer_without_changing_state(
        self, option_ids: tuple[str, ...], other_text: str | None, message: str
    ) -> None:
        question = boundary_question(
            kind=PlanningQuestionKind.MULTIPLE, unknown=True, other=True
        )
        session = boundary_session()
        assert boundary_complete(
            session,
            BOUNDARY_OPERATION_ID,
            1,
            PlanningOperationResult.for_batch(boundary_batch(question)),
            BOUNDARY_NOW,
        )
        with pytest.raises(PlanningAnswersInvalidError, match=message):
            boundary_answer(
                session,
                'batch-1',
                (
                    PlanningAnswer(
                        question_id='q1', option_ids=option_ids, other_text=other_text
                    ),
                ),
                BOUNDARY_NEXT_OPERATION_ID,
                BOUNDARY_NOW,
            )
        assert session.status is PlanningSessionStatus.INTERVIEW
        assert session.answered_batch_count == 0

    def test_should_refuse_answers_restart_and_retry_while_an_operation_runs(
        self,
    ) -> None:
        session = boundary_session()
        with pytest.raises(PlanningOperationConflictError):
            boundary_answer(
                session, 'batch-1', (), BOUNDARY_NEXT_OPERATION_ID, BOUNDARY_NOW
            )
        with pytest.raises(PlanningOperationConflictError):
            boundary_restart(
                session,
                'Outra intenção',
                'rev',
                BOUNDARY_NEXT_OPERATION_ID,
                BOUNDARY_NOW,
            )
        with pytest.raises(PlanningOperationConflictError):
            boundary_retry(session, BOUNDARY_NEXT_OPERATION_ID, BOUNDARY_NOW)
        assert session.operation is not None
        assert session.operation.id == BOUNDARY_OPERATION_ID

    def test_should_refuse_answers_outside_the_interview(self) -> None:
        session = boundary_session()
        assert boundary_complete(
            session,
            BOUNDARY_OPERATION_ID,
            1,
            PlanningOperationResult.for_proposal(boundary_proposal()),
            BOUNDARY_NOW,
        )
        with pytest.raises(PlanningStateConflictError):
            boundary_answer(
                session,
                'batch-1',
                (PlanningAnswer(question_id='q1', option_ids=('o1',)),),
                BOUNDARY_NEXT_OPERATION_ID,
                BOUNDARY_NOW,
            )

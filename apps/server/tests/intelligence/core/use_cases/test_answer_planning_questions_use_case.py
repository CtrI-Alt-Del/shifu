from unittest.mock import create_autospec

import pytest

from shifu.intelligence.core.domain.enums import (
    PlanningOperationKind,
    PlanningQuestionKind,
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.errors import (
    PlanningAnswersInvalidError,
    PlanningOperationConflictError,
    PlanningSessionNotFoundError,
    PlanningStateConflictError,
)
from shifu.intelligence.core.domain.events import (
    PlanningOperationRequestedEvent,
    PlanningOperationRequestedPayload,
)
from shifu.intelligence.core.domain.structures import (
    PlanningAnswer,
    PlanningQuestion,
    PlanningQuestionBatch,
    PlanningOption,
    PlanningOperationResult,
)
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
    OPERATION_ID,
    OTHER_ACCOUNT_ID,
    PLANNING_ID,
    interviewing_session,
    started_session,
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

    @pytest.mark.parametrize(
        ('batch_id', 'answers', 'error'),
        [
            ('missing', _VALID, PlanningStateConflictError),
            ('batch-1', (), PlanningAnswersInvalidError),
            (
                'batch-1',
                (PlanningAnswer(question_id='q9', option_ids=('o1',)),),
                PlanningAnswersInvalidError,
            ),
            (
                'batch-1',
                (PlanningAnswer(question_id='q1', option_ids=()),),
                PlanningAnswersInvalidError,
            ),
            (
                'batch-1',
                (PlanningAnswer(question_id='q1', option_ids=('o1', 'o2')),),
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
    def test_should_reject_mismatched_or_duplicate_batches_without_mutating_history(
        self, batch_id: str, answers: tuple[PlanningAnswer, ...], error: type[Exception]
    ) -> None:
        session = interviewing_session()
        self.sessions.find_by_id.return_value = session

        with pytest.raises(error):
            self.use_case.execute(ACCOUNT_ID, PLANNING_ID, batch_id, answers)

        assert session.status is PlanningSessionStatus.INTERVIEW
        assert session.operation is None
        assert session.answered_batches == ()
        self.sessions.update.assert_not_called()
        self.database.transaction.assert_not_called()

    def _multiple_choice(self) -> None:
        session = started_session()
        question = PlanningQuestion(
            id='q1',
            text='O que construir?',
            kind=PlanningQuestionKind.MULTIPLE,
            options=(
                PlanningOption(id='o1', text='Sites'),
                PlanningOption(id='o2', text='APIs'),
                PlanningOption.other(),
                PlanningOption.unknown(),
            ),
        )
        assert session.complete(
            OPERATION_ID,
            1,
            PlanningOperationResult.for_batch(
                PlanningQuestionBatch(id='batch-1', questions=(question,))
            ),
            NOW,
        )
        self.sessions.find_by_id.return_value = session

    def test_should_record_normalized_open_text_beside_the_selected_alternatives(
        self,
    ) -> None:
        self._multiple_choice()

        result = self.use_case.execute(
            ACCOUNT_ID,
            PLANNING_ID,
            'batch-1',
            (
                PlanningAnswer(
                    question_id='q1',
                    option_ids=('o1', 'outro'),
                    other_text='  planilhas   no Excel ',
                ),
            ),
        )

        item = result.answered_batches[0].items[0]
        assert item.other_text == 'planilhas no Excel'
        assert item.selected_texts == ('Sites',)
        assert item.answer_texts == ('Sites', 'planilhas no Excel')
        self.sessions.update.assert_called_once_with(result)

    @pytest.mark.parametrize(
        ('options', 'text', 'message'),
        [
            (('outro',), None, 'Descreva'),
            (('outro',), '   ', 'Descreva'),
            (('outro',), 'x' * 201, '200 caracteres'),
            (('o1',), 'planilhas', 'exige a alternativa'),
            (('outro', 'nao-sei'), 'planilhas', 'Não sei'),
            (('o1', 'nao-sei'), None, 'Não sei'),
        ],
    )
    def test_should_reject_invalid_open_answers_without_writes(
        self, options: tuple[str, ...], text: str | None, message: str
    ) -> None:
        self._multiple_choice()

        with pytest.raises(PlanningAnswersInvalidError, match=message):
            self.use_case.execute(
                ACCOUNT_ID,
                PLANNING_ID,
                'batch-1',
                (
                    PlanningAnswer(
                        question_id='q1', option_ids=options, other_text=text
                    ),
                ),
            )

        self.sessions.update.assert_not_called()
        self.database.transaction.assert_not_called()

    def test_should_allow_multiple_choices_without_the_exclusive_unknown_option(
        self,
    ) -> None:
        self._multiple_choice()

        result = self.use_case.execute(
            ACCOUNT_ID,
            PLANNING_ID,
            'batch-1',
            (PlanningAnswer(question_id='q1', option_ids=('o1', 'o2')),),
        )

        assert result.answered_batches[0].items[0].selected_texts == ('Sites', 'APIs')

"""The Planner workflow run in process over the disposable PostgreSQL and Redis, with
its four agents replaced by mocks. Planning use cases and the Redis sessions are
real; the intent classifier, the Skill retrieval and the Curriculum catalog are mocks."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import json
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

from agno.run.agent import RunOutput
from agno.run.base import RunStatus
import pytest
from redis import Redis

from shifu.intelligence.ai.agno.agents import (
    PlanningInterviewAgent,
    PlanningProposalAgent,
)
from shifu.intelligence.ai.agno.outputs.planning_interview_output import (
    PlanningInterviewOutput,
    PlanningQuestionOutput,
)
from shifu.intelligence.ai.agno.outputs.planning_proposal_output import (
    PlanningProposalOutput,
    PlanningProposalSkillOutput,
)
from shifu.intelligence.ai.agno.workflows import PlanGoalWorkflow
from shifu.intelligence.core.domain.enums import (
    PlanningIntentKind,
    PlanningOperationStage,
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.errors import (
    PlanningClassificationUnavailableError,
)
from shifu.intelligence.core.domain.structures import (
    PlanningAnswer,
    PlanningIntentClassification,
    PlanningSkillRankEntry,
    PlanningSkillRanking,
)
from shifu.intelligence.core.interfaces import (
    PlanningIntentClassifierProvider,
    PlanningSkillRetrievalProvider,
)
from shifu.intelligence.core.use_cases import (
    AnswerPlanningQuestionsUseCase,
    CancelPlanningUseCase,
    ClassifyPlanningIntentUseCase,
    CompletePlanningOperationUseCase,
    GetPlanningSessionUseCase,
    PreparePlanningOperationUseCase,
    ReportPlanningProgressUseCase,
    RestartPlanningUseCase,
    RetrievePlanningSkillsUseCase,
    RetryPlanningUseCase,
    StartPlanningUseCase,
)
from shifu.intelligence.providers.planning.redis.redis_planning_sessions_repository import (
    RedisPlanningSessionsRepository,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import (
    MentorAccessGrant,
    SkillCatalogEntry,
    SkillFoundationEntry,
)
from shifu.shared.core.interfaces import CurriculumCatalogProvider, MentorAccessProvider
from shifu.shared.messaging.agentos.agentos_handoff_store import AgentOSHandoffStore
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.intelligence_fixture import MENTOR_ACCOUNT

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shifu.intelligence.core.domain.entities import PlanningSession
    from tests.fixtures.intelligence_fixture import IntelligenceFixture
    from tests.fixtures.redis_fixture import RedisFixture

HTML_ID = '01J0000000000000000000HTML'
JAVASCRIPT_ID = '01J00000000000000000000JS0'
REACT_ID = '01J0000000000000000000RCT0'
_SKILLS = (
    SkillCatalogEntry(
        id=HTML_ID, name='HTML e CSS', description='Estrutura e estilo de páginas.'
    ),
    SkillCatalogEntry(
        id=JAVASCRIPT_ID,
        name='JavaScript essencial',
        description='Lógica e interatividade no navegador.',
    ),
    SkillCatalogEntry(
        id=REACT_ID, name='React', description='Interfaces com componentes.'
    ),
)
_ALLOWED_PAYLOAD_KEYS = {
    'intent',
    'answers',
    'candidates',
    'remaining_batches',
    'problems',
}


def completed(content: PlanningInterviewOutput | PlanningProposalOutput) -> RunOutput:
    """A completed agent run, as a mocked Planner agent returns it."""
    return RunOutput(content=content, status=RunStatus.completed)


def sufficient() -> RunOutput:
    return completed(PlanningInterviewOutput(needs_clarification=False, questions=[]))


def clarification() -> RunOutput:
    return completed(
        PlanningInterviewOutput(
            needs_clarification=True,
            questions=[
                PlanningQuestionOutput(
                    text='O que você quer construir primeiro?',
                    kind='single',
                    options=['Páginas e layout', 'Interatividade', 'Outro'],
                    allow_unknown=True,
                )
            ],
        )
    )


def web_proposal() -> RunOutput:
    return completed(
        PlanningProposalOutput(
            supported=True,
            title='Aprender desenvolvimento web',
            description='Um caminho do HTML ao React para construir sites.',
            skills=[
                PlanningProposalSkillOutput(
                    skill_id=skill.id, justification=f'{skill.name} sustenta o site.'
                )
                for skill in _SKILLS
            ],
        )
    )


def invalid_draft() -> RunOutput:
    return completed(
        PlanningProposalOutput(
            supported=True,
            title='Aprender web',
            description='Duplicada.',
            skills=[
                PlanningProposalSkillOutput(
                    skill_id='skill-ghost', justification='Não existe.'
                ),
                PlanningProposalSkillOutput(
                    skill_id='skill-ghost', justification='Repetida.'
                ),
            ],
        )
    )


def declined() -> RunOutput:
    return completed(
        PlanningProposalOutput(supported=False, title='', description='', skills=[])
    )


def classification(kind: PlanningIntentKind) -> PlanningIntentClassification:
    others = [other for other in PlanningIntentKind if other is not kind]
    return PlanningIntentClassification(
        kind=kind,
        confidence=0.9,
        probabilities=(
            (kind.value, 0.9),
            (others[0].value, 0.05),
            (others[1].value, 0.05),
        ),
    )


def ranking() -> PlanningSkillRanking:
    identifiers = tuple(skill.id for skill in _SKILLS)
    scores = {skill_id: 1 / (60 + rank) for rank, skill_id in enumerate(identifiers, 1)}
    return PlanningSkillRanking(
        index_version='planner-test',
        lexical_ranking=identifiers,
        semantic_ranking=(),
        entries=tuple(
            PlanningSkillRankEntry(
                skill_id=skill_id, score=score, lexical_rank=rank, semantic_rank=None
            )
            for rank, (skill_id, score) in enumerate(
                sorted(scores.items(), key=lambda item: (-item[1], item[0])), 1
            )
        ),
    )


def grant(account_id: str, operation_key: str) -> MentorAccessGrant:
    return MentorAccessGrant(
        account_id=account_id, access_revision='revision-1', operation_key=operation_key
    )


def payloads(agent: Mock) -> list[dict[str, object]]:
    """The JSON inputs the workflow sent to one mocked agent, in call order."""
    return [
        cast('dict[str, object]', json.loads(cast('str', call.kwargs['input'])))
        for call in agent.run.call_args_list
    ]


@dataclass
class Harness:
    fixture: IntelligenceFixture
    sessions: RedisPlanningSessionsRepository
    workflow: PlanGoalWorkflow
    access: Mock
    classifier: Mock
    interview: Mock
    proposal: Mock
    retrieval: Mock

    def start(self, intent: str) -> PlanningSession:
        return StartPlanningUseCase(
            self.sessions,
            self.fixture.database,
            self.access,
            SystemIdentifierProvider(),
            SystemClockProvider(),
        ).execute(MENTOR_ACCOUNT.account_id, intent)

    def run(self, session: PlanningSession) -> PlanningSession | None:
        operation = session.operation
        assert operation is not None
        # The registered runtime runs the workflow asynchronously; so does the test.
        asyncio.run(
            self.workflow.arun(
                input=json.dumps(
                    {
                        'planning_id': session.id,
                        'operation_id': operation.id,
                        'generation': str(session.generation),
                    }
                )
            )
        )
        return self.sessions.find_by_id(session.id)

    def answer(
        self,
        session: PlanningSession,
        option_index: int,
        other_text: str | None = None,
    ) -> PlanningSession:
        batch = session.current_batch
        assert batch is not None
        question = batch.questions[0]
        return AnswerPlanningQuestionsUseCase(
            self.sessions,
            self.fixture.database,
            SystemIdentifierProvider(),
            SystemClockProvider(),
        ).execute(
            MENTOR_ACCOUNT.account_id,
            session.id,
            batch.id,
            (
                PlanningAnswer(
                    question_id=question.id,
                    option_ids=(question.options[option_index].id,),
                    other_text=other_text,
                ),
            ),
        )

    def retry(self, session: PlanningSession) -> PlanningSession:
        return RetryPlanningUseCase(
            self.sessions,
            self.fixture.database,
            SystemIdentifierProvider(),
            SystemClockProvider(),
        ).execute(MENTOR_ACCOUNT.account_id, session.id)

    def restart(self, session: PlanningSession, intent: str) -> PlanningSession:
        return RestartPlanningUseCase(
            self.sessions,
            self.fixture.database,
            self.access,
            SystemIdentifierProvider(),
            SystemClockProvider(),
        ).execute(MENTOR_ACCOUNT.account_id, session.id, intent)

    def model_calls(self) -> int:
        return self.interview.run.call_count + self.proposal.run.call_count


@pytest.fixture
def harness(
    intelligence_fixture: IntelligenceFixture, redis_fixture: RedisFixture
) -> Iterator[Harness]:
    client = Redis.from_url(  # pyright: ignore[reportUnknownMemberType] - redis-py defers option typing.
        redis_fixture.url, decode_responses=True
    )
    sessions = RedisPlanningSessionsRepository(client, 3600)
    clock = SystemClockProvider()
    access = Mock(spec=MentorAccessProvider)
    access.authorize.side_effect = grant
    classifier = Mock(spec=PlanningIntentClassifierProvider)
    classifier.classify.return_value = classification(PlanningIntentKind.LEARNING)
    retrieval = Mock(spec=PlanningSkillRetrievalProvider)
    retrieval.retrieve.return_value = ranking()
    catalog = Mock(spec=CurriculumCatalogProvider)
    catalog.list_skills.return_value = _SKILLS
    catalog.find_direct_foundations_for_many.return_value = {
        REACT_ID: [SkillFoundationEntry(skill_id=JAVASCRIPT_ID, name='JavaScript')]
    }
    interview = Mock(spec=PlanningInterviewAgent)
    interview.run.return_value = sufficient()
    proposal = Mock(spec=PlanningProposalAgent)
    proposal.run.return_value = web_proposal()
    workflow = PlanGoalWorkflow(
        prepare_use_case=PreparePlanningOperationUseCase(sessions, access),
        complete_use_case=CompletePlanningOperationUseCase(sessions, clock),
        progress_use_case=ReportPlanningProgressUseCase(sessions, clock),
        classify_use_case=ClassifyPlanningIntentUseCase(classifier),
        retrieve_use_case=RetrievePlanningSkillsUseCase(retrieval, catalog),
        interview_agent=interview,
        proposal_agent=proposal,
        identifier_provider=SystemIdentifierProvider(),
        handoffs=AgentOSHandoffStore(),
    )
    try:
        yield Harness(
            fixture=intelligence_fixture,
            sessions=sessions,
            workflow=workflow,
            access=access,
            classifier=classifier,
            interview=interview,
            proposal=proposal,
            retrieval=retrieval,
        )
    finally:
        client.close()


class TestPlanGoalWorkflow:
    def test_should_compose_a_proposal_directly_for_a_sufficient_intent(
        self, harness: Harness
    ) -> None:
        session = harness.start(
            'Quero aprender a construir sites com HTML, CSS e React'
        )

        final = harness.run(session)

        assert final is not None
        assert final.status is PlanningSessionStatus.PROPOSAL
        assert final.consulted_curriculum is True
        assert final.proposal is not None
        names = {skill.name for skill in final.proposal.skills}
        assert names == {'HTML e CSS', 'JavaScript essencial', 'React'}
        assert [
            (relation.skill_id, relation.foundation_skill_id)
            for relation in final.proposal.relations
        ] == [(REACT_ID, JAVASCRIPT_ID)]
        # Only the intent, the answers and the candidate texts reach the model.
        requests = payloads(harness.interview) + payloads(harness.proposal)
        assert len(requests) == 2
        assert all(set(request) <= _ALLOWED_PAYLOAD_KEYS for request in requests)

    def test_should_send_the_open_answer_to_the_search_and_the_proposal(
        self, harness: Harness
    ) -> None:
        harness.interview.run.side_effect = [clarification(), sufficient()]
        session = harness.start('Quero aprender a fazer sites')
        interview = harness.run(session)
        assert interview is not None
        batch = interview.current_batch
        assert batch is not None
        other_index = next(
            index
            for index, option in enumerate(batch.questions[0].options)
            if option.open
        )

        final = harness.run(
            harness.answer(interview, other_index, other_text='Landing pages')
        )

        assert final is not None
        assert final.status is PlanningSessionStatus.PROPOSAL
        assert payloads(harness.proposal)[-1]['answers'] == [
            {
                'question': 'O que você quer construir primeiro?',
                'kind': 'single',
                'selected': [],
                'other_text': 'Landing pages',
            }
        ]
        query = harness.retrieval.retrieve.call_args.args[0]
        assert query.answers == ('Landing pages',)

    def test_should_ask_a_batch_and_compose_after_the_answers(
        self, harness: Harness
    ) -> None:
        harness.interview.run.side_effect = [clarification(), sufficient()]
        session = harness.start('Quero aprender a fazer sites')

        interview = harness.run(session)

        assert interview is not None
        assert interview.status is PlanningSessionStatus.INTERVIEW
        batch = interview.current_batch
        assert batch is not None
        options = batch.questions[0].options
        assert [option.text for option in options] == [
            'Páginas e layout',
            'Interatividade',
            'Outro',
            'Não sei',
        ]
        assert options[-2].open is True
        assert options[-1].exclusive is True

        final = harness.run(harness.answer(interview, 1))

        assert final is not None
        assert final.status is PlanningSessionStatus.PROPOSAL
        assert len(final.answered_batches) == 1
        assert final.current_batch is None
        assert payloads(harness.proposal)[-1]['answers'] == [
            {
                'question': 'O que você quer construir primeiro?',
                'kind': 'single',
                'selected': ['Interatividade'],
                'other_text': None,
            }
        ]
        assert harness.classifier.classify.call_count == 1

    def test_should_end_out_of_scope_without_calling_the_model(
        self, harness: Harness
    ) -> None:
        harness.classifier.classify.return_value = classification(
            PlanningIntentKind.OUT_OF_SCOPE
        )
        session = harness.start('Quero comprar um notebook barato')

        final = harness.run(session)

        assert final is not None
        assert final.status is PlanningSessionStatus.OUT_OF_SCOPE
        assert final.message
        assert final.current_batch is None
        assert final.proposal is None
        assert final.consulted_curriculum is False
        assert harness.model_calls() == 0

    def test_should_report_unsupported_when_the_composer_declines(
        self, harness: Harness
    ) -> None:
        harness.proposal.run.return_value = declined()
        session = harness.start('Quero aprender a tocar violão')

        final = harness.run(session)

        assert final is not None
        assert final.status is PlanningSessionStatus.UNSUPPORTED
        assert final.message
        assert final.proposal is None

    def test_should_correct_an_invalid_draft_before_exposing_a_proposal(
        self, harness: Harness
    ) -> None:
        harness.proposal.run.side_effect = [invalid_draft(), web_proposal()]
        session = harness.start('Quero aprender React')

        final = harness.run(session)

        assert final is not None
        assert final.status is PlanningSessionStatus.PROPOSAL
        requests = payloads(harness.proposal)
        assert len(requests) == 2
        assert requests[0]['problems'] == []
        problems = cast('list[str]', requests[1]['problems'])
        assert any('não existe' in problem for problem in problems)

    def test_should_fail_validation_after_four_invalid_drafts(
        self, harness: Harness
    ) -> None:
        harness.proposal.run.side_effect = [invalid_draft() for _ in range(4)]
        session = harness.start('Quero aprender React')

        final = harness.run(session)

        assert final is not None
        assert final.status is PlanningSessionStatus.VALIDATION_FAILED
        assert final.failure_code == 'validation_exhausted'
        assert final.proposal is None
        assert harness.proposal.run.call_count == 4

    def test_should_fail_recoverably_when_the_model_fails(
        self, harness: Harness
    ) -> None:
        harness.interview.run.side_effect = ServiceUnavailableError(
            'The Planner model is unavailable.'
        )
        session = harness.start('Quero aprender React')

        final = harness.run(session)

        assert final is not None
        assert final.status is PlanningSessionStatus.FAILED
        assert final.failure_code == 'service_unavailable'
        assert final.proposal is None
        harness.proposal.run.assert_not_called()

    def test_should_fail_recoverably_when_the_model_breaks_the_schema(
        self, harness: Harness
    ) -> None:
        harness.proposal.run.return_value = RunOutput(
            content='não é JSON', status=RunStatus.completed
        )
        session = harness.start('Quero aprender React')

        final = harness.run(session)

        assert final is not None
        assert final.status is PlanningSessionStatus.FAILED
        assert final.failure_code == 'service_unavailable'
        assert final.proposal is None

    def test_should_recover_from_a_classification_failure_through_retry(
        self, harness: Harness
    ) -> None:
        harness.classifier.classify.side_effect = [
            PlanningClassificationUnavailableError(),
            classification(PlanningIntentKind.LEARNING),
        ]
        session = harness.start('Quero aprender React')

        failed = harness.run(session)

        assert failed is not None
        assert failed.status is PlanningSessionStatus.FAILED
        assert failed.failure_code == 'service_unavailable'
        assert failed.intent == 'Quero aprender React'

        recovered = harness.run(harness.retry(failed))

        assert recovered is not None
        assert recovered.status is PlanningSessionStatus.PROPOSAL

    def test_should_discard_a_late_result_after_cancel(self, harness: Harness) -> None:
        session = harness.start('Quero aprender a fazer sites')

        def cancel_then_answer(**_kwargs: object) -> RunOutput:
            CancelPlanningUseCase(harness.sessions).execute(
                MENTOR_ACCOUNT.account_id, session.id
            )
            return sufficient()

        harness.interview.run.side_effect = cancel_then_answer

        final = harness.run(session)

        assert final is None

    def test_should_discard_a_late_result_of_a_restarted_generation(
        self, harness: Harness
    ) -> None:
        session = harness.start('Quero aprender a fazer sites')
        restarted: list[PlanningSession] = []

        def restart_then_answer(**_kwargs: object) -> RunOutput:
            # The workflow reported its stage before asking the interview model.
            in_flight = harness.sessions.find_by_id(session.id)
            assert in_flight is not None
            assert in_flight.operation is not None
            assert in_flight.operation.stage is PlanningOperationStage.INTERVIEWING
            # A running operation cannot be restarted: the learner first sees it
            # expire, then restarts, and only then does the old run answer.
            expired = GetPlanningSessionUseCase(
                harness.sessions, SystemClockProvider(), timedelta(0)
            ).execute(MENTOR_ACCOUNT.account_id, session.id)
            assert expired.failure_code == 'operation_timeout'
            restarted.append(harness.restart(session, 'Quero aprender React'))
            return sufficient()

        harness.interview.run.side_effect = restart_then_answer

        final = harness.run(session)

        assert final is not None
        assert final.generation == restarted[0].generation == session.generation + 1
        assert final.status is PlanningSessionStatus.PROCESSING
        assert final.intent == 'Quero aprender React'
        assert final.proposal is None

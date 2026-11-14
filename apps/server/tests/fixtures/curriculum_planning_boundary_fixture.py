from __future__ import annotations
from datetime import UTC, datetime, timedelta
from shifu.intelligence.core.domain.enums import (
    PlanningOperationStage,
    PlanningQuestionKind,
)
from shifu.intelligence.core.domain.errors import (
    PlanningAnswersInvalidError,
    PlanningOperationConflictError,
    PlanningStateConflictError,
)
from shifu.intelligence.core.domain.structures import (
    PlanningAnswer,
    PlanningOperationResult,
    PlanningOption,
    PlanningProposal,
    PlanningProposalSkill,
    PlanningQuestion,
    PlanningQuestionBatch,
)
from unittest.mock import create_autospec
from shifu.intelligence.core.interfaces import (
    PlanningSessionsRepository,
    IntelligenceDatabase,
)
from shifu.intelligence.core.use_cases import (
    StartPlanningUseCase,
    AnswerPlanningQuestionsUseCase,
    RestartPlanningUseCase,
    RetryPlanningUseCase,
    CompletePlanningOperationUseCase,
    ReportPlanningProgressUseCase,
    GetPlanningSessionUseCase,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
)
from shifu.shared.core.domain.structures import MentorAccessGrant
import json
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast
import httpx
import pytest
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.curriculum.providers import DatabaseCurriculumCatalogProvider
from shifu.intelligence.ai.data.planner_resources import PlannerResources
from shifu.intelligence.core.domain.enums import PlanningIntentKind
from shifu.intelligence.core.domain.structures import (
    PlanningQuery,
    PlanningSkillRanking,
    PlanningSkillRankEntry,
)
from shifu.intelligence.core.domain.structures.planning_indexed_embedding import (
    PLANNING_EMBEDDING_DIMENSION,
)
from shifu.intelligence.core.use_cases import (
    ClassifyPlanningIntentUseCase,
    RetrievePlanningSkillsUseCase,
)
from shifu.intelligence.database.planning_embeddings_database_repository import (
    PlanningEmbeddingsDatabaseRepository,
)
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.prepare_planning_indexes import prepare_indexes
from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
    SentenceTransformersEmbeddingsProvider,
)
from shifu.intelligence.providers.planning.intent_classification.openrouter.jev_planning_intent_classifier_provider import (
    JevPlanningIntentClassifierProvider,
)
from shifu.intelligence.providers.planning.retrieval.sklearn.tfidf_sentence_transformers_planning_skill_retrieval_provider import (
    TfidfSentenceTransformersPlanningSkillRetrievalProvider,
)
from shifu.intelligence.providers.planning.text_preprocessing.spacy.spacy_planning_text_preprocessor_provider import (
    SpacyPlanningTextPreprocessorProvider,
)
from shifu.shared.database.seed_data import build_development_seed
from shifu.intelligence.core.interfaces import (
    MentorEmbeddingsProvider,
    PlanningTextPreprocessorProvider,
)
from shifu.shared.core.interfaces import CurriculumCatalogProvider
from shifu.shared.core.domain.structures import SkillCatalogEntry
from shifu.intelligence.core.domain.structures import PlanningIndexedEmbedding


if TYPE_CHECKING:
    from sqlalchemy import Engine
    from shifu.intelligence.core.domain.entities import PlanningSession


BOUNDARY_NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
BOUNDARY_PLANNING_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
BOUNDARY_OPERATION_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAW'
BOUNDARY_NEXT_OPERATION_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAX'


def boundary_question(
    question_id: str = 'q1',
    kind: PlanningQuestionKind = PlanningQuestionKind.SINGLE,
    *,
    unknown: bool = False,
    other: bool = False,
) -> PlanningQuestion:
    options = [
        PlanningOption(id='o1', text='Sites'),
        PlanningOption(id='o2', text='APIs'),
    ]
    if other:
        options.append(PlanningOption.other())
    if unknown:
        options.append(PlanningOption.unknown())
    return PlanningQuestion(
        id=question_id,
        text='O que você quer construir?',
        kind=kind,
        options=tuple(options),
    )


def boundary_batch(*questions: PlanningQuestion) -> PlanningQuestionBatch:
    return PlanningQuestionBatch(
        id='batch-1', questions=questions or (boundary_question(),)
    )


def boundary_proposal(*skill_ids: str) -> PlanningProposal:
    return PlanningProposal(
        title='Aprender web',
        description='Do HTML ao React.',
        skills=tuple(
            PlanningProposalSkill(
                skill_id=skill_id, name=f'Skill {skill_id}', justification='Base.'
            )
            for skill_id in skill_ids or ('skill-a',)
        ),
    )


def boundary_session() -> PlanningSession:
    return boundary_start(
        BOUNDARY_PLANNING_ID,
        'account-1',
        'revision-1',
        '  Quero   aprender  web ',
        BOUNDARY_OPERATION_ID,
        BOUNDARY_NOW,
    )


def boundary_interviewing() -> PlanningSession:
    session = boundary_session()
    assert boundary_complete(
        session,
        BOUNDARY_OPERATION_ID,
        1,
        PlanningOperationResult.for_batch(boundary_batch()),
        BOUNDARY_NOW,
    )
    return session


def boundary_start(
    planning_id: str,
    account_id: str,
    revision: str,
    intent: str,
    operation_id: str,
    now: datetime,
) -> PlanningSession:
    sessions = create_autospec(PlanningSessionsRepository, instance=True)
    database = create_autospec(IntelligenceDatabase, instance=True)
    access = create_autospec(MentorAccessProvider, instance=True)
    access.authorize.return_value = MentorAccessGrant(
        account_id=account_id, access_revision=revision, operation_key=planning_id
    )
    identifiers = create_autospec(IdentifierProvider, instance=True)
    identifiers.generate.side_effect = [planning_id, operation_id]
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = now
    try:
        return StartPlanningUseCase(
            sessions, database, access, identifiers, clock
        ).execute(account_id, intent)
    except ValueError:
        sessions.add.assert_not_called()
        database.transaction.assert_not_called()
        raise


def boundary_complete(
    session: PlanningSession,
    operation_id: str,
    generation: int,
    result: PlanningOperationResult,
    now: datetime,
) -> bool:
    sessions = create_autospec(PlanningSessionsRepository, instance=True)
    sessions.find_by_id.return_value = session
    sessions.update.return_value = True
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = now
    return CompletePlanningOperationUseCase(sessions, clock).execute(
        session.id, operation_id, generation, result
    )


def boundary_answer(
    session: PlanningSession,
    batch_id: str,
    answers: tuple[PlanningAnswer, ...],
    operation_id: str,
    now: datetime,
) -> PlanningSession:
    sessions = create_autospec(PlanningSessionsRepository, instance=True)
    sessions.find_by_id.return_value = session
    sessions.update.return_value = True
    database = create_autospec(IntelligenceDatabase, instance=True)
    identifiers = create_autospec(IdentifierProvider, instance=True)
    identifiers.generate.return_value = operation_id
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = now
    try:
        return AnswerPlanningQuestionsUseCase(
            sessions, database, identifiers, clock
        ).execute(session.account_id, session.id, batch_id, answers)
    except (
        PlanningAnswersInvalidError,
        PlanningOperationConflictError,
        PlanningStateConflictError,
    ):
        sessions.update.assert_not_called()
        database.transaction.assert_not_called()
        raise


def boundary_restart(
    session: PlanningSession,
    intent: str,
    revision: str,
    operation_id: str,
    now: datetime,
) -> PlanningSession:
    sessions = create_autospec(PlanningSessionsRepository, instance=True)
    sessions.find_by_id.return_value = session
    sessions.update.return_value = True
    database = create_autospec(IntelligenceDatabase, instance=True)
    access = create_autospec(MentorAccessProvider, instance=True)
    access.authorize.return_value = MentorAccessGrant(
        account_id=session.account_id,
        access_revision=revision,
        operation_key=session.id,
    )
    identifiers = create_autospec(IdentifierProvider, instance=True)
    identifiers.generate.return_value = operation_id
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = now
    return RestartPlanningUseCase(
        sessions, database, access, identifiers, clock
    ).execute(session.account_id, session.id, intent)


def boundary_retry(
    session: PlanningSession, operation_id: str, now: datetime
) -> PlanningSession:
    sessions = create_autospec(PlanningSessionsRepository, instance=True)
    sessions.find_by_id.return_value = session
    sessions.update.return_value = True
    database = create_autospec(IntelligenceDatabase, instance=True)
    identifiers = create_autospec(IdentifierProvider, instance=True)
    identifiers.generate.return_value = operation_id
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = now
    return RetryPlanningUseCase(sessions, database, identifiers, clock).execute(
        session.account_id, session.id
    )


def boundary_progress(
    session: PlanningSession,
    operation_id: str,
    generation: int,
    stage: PlanningOperationStage,
    now: datetime,
) -> bool:
    sessions = create_autospec(PlanningSessionsRepository, instance=True)
    sessions.find_by_id.return_value = session
    sessions.update.return_value = True
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = now
    return ReportPlanningProgressUseCase(sessions, clock).execute(
        session.id, operation_id, generation, stage
    )


def boundary_expire(
    session: PlanningSession, now: datetime, timeout: timedelta
) -> bool:
    sessions = create_autospec(PlanningSessionsRepository, instance=True)
    sessions.find_by_id.return_value = session
    sessions.update.return_value = True
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = now
    GetPlanningSessionUseCase(sessions, clock, timeout).execute(
        session.account_id, session.id
    )
    return sessions.update.called


@dataclass(frozen=True)
class BoundaryCorpus:
    engine: Engine
    catalog: DatabaseCurriculumCatalogProvider
    database: SqlalchemyIntelligenceDatabase
    repository: PlanningEmbeddingsDatabaseRepository
    ids_by_name: dict[str, str]
    names_by_id: dict[str, str]


@dataclass(frozen=True)
class BoundaryIndex:
    corpus: BoundaryCorpus
    resources: PlannerResources
    version: str
    provider: TfidfSentenceTransformersPlanningSkillRetrievalProvider


@dataclass
class BoundaryJevDouble:
    """Transport double of the decisions endpoint keyed by the labeled intent."""

    labels: dict[str, PlanningIntentKind]
    confidence: float = 0.9
    requests: list[dict[str, Any]] = field(default_factory=list)

    def handler(self, request: httpx.Request) -> httpx.Response:
        payload = cast('dict[str, Any]', json.loads(request.content))
        self.requests.append(payload)
        assert request.headers['authorization'] == 'Bearer test-key'
        assert payload['model'] == BOUNDARY_MODEL
        assert set(payload['questions']) == {
            JevPlanningIntentClassifierProvider.QUESTION
        }
        question = payload['questions'][JevPlanningIntentClassifierProvider.QUESTION]
        assert question['type'] == 'choice'
        assert set(question['criteria']) == set(BOUNDARY_KINDS)
        # Only the current intent and the submitted answers leave the process.
        assert set(payload['state']) == {'intent', 'answers'}
        assert payload['provider'] == {'zdr': True, 'data_collection': 'deny'}
        label = self.labels[payload['state']['intent']]
        return boundary_decision(label.value, self.confidence)


class BoundaryShortEmbeddings:
    """Embeddings double with the wrong dimension for the preparation guard."""

    def embed_queries(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple((0.0, 0.0, 1.0) for _ in texts)

    def embed_passages(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple((0.0, 0.0, 1.0) for _ in texts)


if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from tests.fixtures.postgres_fixture import PostgresDatabase

BOUNDARY_DECISIONS_URL = 'https://openrouter.test/api/alpha/decisions'

BOUNDARY_MODEL = 'typesafe/jev-1.13'

BOUNDARY_KINDS = tuple(kind.value for kind in PlanningIntentKind)


def boundary_decision(choice: str, confidence: float) -> httpx.Response:
    rest = (1 - confidence) / 2
    return httpx.Response(
        200,
        json={
            'answers': {
                JevPlanningIntentClassifierProvider.QUESTION: {
                    'type': 'choice',
                    'choice': choice,
                    'confidence': confidence,
                    'probabilities': {
                        kind: confidence if kind == choice else rest
                        for kind in BOUNDARY_KINDS
                    },
                }
            }
        },
    )


def boundary_classifier(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    api_key: str | None = 'test-key',
) -> JevPlanningIntentClassifierProvider:
    return JevPlanningIntentClassifierProvider(
        httpx.Client(transport=httpx.MockTransport(handler)),
        api_key,
        BOUNDARY_DECISIONS_URL,
        BOUNDARY_MODEL,
        PlannerResources().manifest.intent_thresholds,
    )


def boundary_evaluate(
    use_case: ClassifyPlanningIntentUseCase,
    items: Iterable[tuple[str, PlanningIntentKind]],
) -> tuple[Counter[tuple[str, str]], float, int]:
    matrix: Counter[tuple[str, str]] = Counter()
    total = correct = undue_refusals = 0
    for text, label in items:
        predicted = use_case.execute(PlanningQuery(intent=text)).kind
        matrix[label.value, predicted.value] += 1
        total += 1
        correct += predicted is label
        undue_refusals += (
            label is PlanningIntentKind.LEARNING
            and predicted is PlanningIntentKind.OUT_OF_SCOPE
        )
    return matrix, correct / total, undue_refusals


def boundary_print_matrix(title: str, matrix: Counter[tuple[str, str]]) -> None:
    print(f'\n[{title}] confusion matrix (rows: expected, columns: predicted)')
    print(f'{"":<14}' + ''.join(f'{kind:>14}' for kind in BOUNDARY_KINDS))
    for expected in BOUNDARY_KINDS:
        print(
            f'{expected:<14}'
            + ''.join(
                f'{matrix[expected, predicted]:>14}' for predicted in BOUNDARY_KINDS
            )
        )


def boundary_query(intent: str, answers: Sequence[str] = ()) -> PlanningQuery:
    return PlanningQuery(intent=intent, answers=tuple(answers))


def boundary_names(index: BoundaryIndex, skill_ids: Iterable[str]) -> list[str]:
    return [index.corpus.names_by_id[skill_id] for skill_id in skill_ids]


def boundary_entry_names(
    index: BoundaryIndex, ranking: PlanningSkillRanking
) -> list[str]:
    return boundary_names(index, (entry.skill_id for entry in ranking.entries))


def boundary_no_sleep(_seconds: float) -> None:
    return None


def boundary_axis(position: int) -> tuple[float, ...]:
    vector = [0.0] * PLANNING_EMBEDDING_DIMENSION
    vector[position] = 1.0
    return tuple(vector)


@pytest.fixture(scope='module')
def embeddings() -> SentenceTransformersEmbeddingsProvider:
    return SentenceTransformersEmbeddingsProvider()


@pytest.fixture(scope='module')
def preprocessor() -> SpacyPlanningTextPreprocessorProvider:
    return SpacyPlanningTextPreprocessorProvider(PlannerResources().manifest.negation)


@pytest.fixture
def corpus(postgres_database: PostgresDatabase) -> BoundaryCorpus:
    seed = build_development_seed()
    curriculum = SqlalchemyCurriculumDatabase(postgres_database.engine)
    with curriculum.transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
    catalog = DatabaseCurriculumCatalogProvider(curriculum)
    database = SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)
    skills = catalog.list_skills()
    return BoundaryCorpus(
        engine=postgres_database.engine,
        catalog=catalog,
        database=database,
        repository=PlanningEmbeddingsDatabaseRepository(database),
        ids_by_name={skill.name: skill.id for skill in skills},
        names_by_id={skill.id: skill.name for skill in skills},
    )


@pytest.fixture
def index(
    corpus: BoundaryCorpus,
    embeddings: SentenceTransformersEmbeddingsProvider,
    preprocessor: SpacyPlanningTextPreprocessorProvider,
) -> BoundaryIndex:
    resources = PlannerResources()
    version = prepare_indexes(
        embeddings, corpus.repository, corpus.catalog, resources, preprocessor
    )
    provider = TfidfSentenceTransformersPlanningSkillRetrievalProvider(
        corpus.catalog.list_skills(),
        embeddings,
        corpus.repository,
        preprocessor,
        resources,
    )
    return BoundaryIndex(corpus, resources, version, provider)


def boundary_set_dimension(data: dict[str, Any]) -> None:
    data['dimension'] = 512


def boundary_break_threshold(data: dict[str, Any]) -> None:
    data['intent_thresholds']['learning'] = 1.5


def boundary_empty_held_out(data: dict[str, Any]) -> None:
    data['held_out'] = []


def boundary_empty_queries(data: dict[str, Any]) -> None:
    data['queries'] = []


def retrieve_index(index: BoundaryIndex, query: PlanningQuery) -> PlanningSkillRanking:
    retrieval = RetrievePlanningSkillsUseCase(
        index.provider, index.corpus.catalog
    ).execute(query)
    return PlanningSkillRanking(
        index_version=retrieval.index_version,
        lexical_ranking=retrieval.lexical_ranking,
        semantic_ranking=retrieval.semantic_ranking,
        entries=tuple(
            PlanningSkillRankEntry(
                skill_id=item.skill_id,
                score=item.score,
                lexical_rank=item.lexical_rank,
                semantic_rank=item.semantic_rank,
            )
            for item in retrieval.candidates
        ),
    )


def prepare_corpus(
    repository: PlanningEmbeddingsDatabaseRepository,
    version: str,
    corpus: tuple[PlanningIndexedEmbedding, ...],
) -> None:
    """Enter public preparation with controlled inference vectors to isolate SQL lifecycle contracts."""
    embeddings_port = create_autospec(MentorEmbeddingsProvider, instance=True)
    embeddings_port.embed_passages.return_value = tuple(item.vector for item in corpus)
    catalog_port = create_autospec(CurriculumCatalogProvider, instance=True)
    catalog_port.list_skills.return_value = tuple(
        SkillCatalogEntry(
            id=item.skill_id, name=item.skill_id, description='Lifecycle corpus'
        )
        for item in corpus
    )
    preprocessor_port = create_autospec(PlanningTextPreprocessorProvider, instance=True)

    def normalized(text: str) -> str:
        return text

    preprocessor_port.normalize.side_effect = normalized
    resources = PlannerResources()

    def bind_catalog(skills: tuple[SkillCatalogEntry, ...]) -> None:
        del skills

    resources.bind_catalog = bind_catalog
    resources.version = version
    prepare_indexes(
        embeddings_port, repository, catalog_port, resources, preprocessor_port
    )

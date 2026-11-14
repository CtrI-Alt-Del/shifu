from __future__ import annotations
import httpx
import pytest
from shifu.intelligence.ai.data.planner_resources import PlannerResources
from shifu.intelligence.core.domain.enums import PlanningIntentKind
from shifu.intelligence.core.domain.errors import (
    PlanningClassificationUnavailableError,
)
from shifu.intelligence.core.domain.structures import (
    PlanningQuery,
)
from shifu.intelligence.core.use_cases import (
    ClassifyPlanningIntentUseCase,
    RetrievePlanningSkillsUseCase,
)
from shifu.intelligence.providers.planning.intent_classification.openrouter import (
    jev_planning_intent_classifier_provider as jev_module,
)
from shifu.intelligence.providers.planning.intent_classification.openrouter.jev_planning_intent_classifier_provider import (
    JevPlanningIntentClassifierProvider,
)
from tests.fixtures.curriculum_planning_boundary_fixture import (
    BoundaryIndex,
    BoundaryJevDouble,
    boundary_decision,
    boundary_classifier,
    boundary_evaluate,
    boundary_print_matrix,
    boundary_query,
    boundary_entry_names,
    boundary_no_sleep,
    retrieve_index,
    BOUNDARY_DECISIONS_URL,
    BOUNDARY_MODEL,
)
from tests.fixtures.curriculum_planning_boundary_fixture import (
    corpus as corpus,
    index as index,
    embeddings as embeddings,
    preprocessor as preprocessor,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shifu.intelligence.providers.planning.text_preprocessing.spacy.spacy_planning_text_preprocessor_provider import (
        SpacyPlanningTextPreprocessorProvider,
    )
    from collections.abc import Callable


class TestPlanningSkillRetrieval:
    def test_should_lemmatize_drop_stop_words_and_keep_negation(
        self,
        index: BoundaryIndex,
        preprocessor: SpacyPlanningTextPreprocessorProvider,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: list[tuple[str, ...]] = []
        original = preprocessor.lexical_tokens

        def record_tokens(text: str) -> tuple[str, ...]:
            tokens = original(text)
            captured.append(tokens)
            return tokens

        monkeypatch.setattr(preprocessor, 'lexical_tokens', record_tokens)

        def through_retrieval(text: str) -> tuple[str, ...]:
            retrieve_index(index, boundary_query(text))
            return captured[-1]

        tokens = through_retrieval(
            'Não quero front-end, prefiro APIs e bancos de dados'
        )
        assert tokens[0] == 'não'
        assert 'front-end' in tokens
        assert 'banco' in tokens
        assert 'dado' in tokens
        assert not {'bancos', 'dados', 'e', 'de', 'quero', ','} & set(tokens)
        assert 'nunca' in through_retrieval(
            'Nunca programei e quero começar pelo básico'
        )
        assert 'nem' in through_retrieval('Nem web nem interfaces')

    def test_should_keep_the_full_sentence_for_the_semantic_representation(
        self,
        index: BoundaryIndex,
        preprocessor: SpacyPlanningTextPreprocessorProvider,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        normalized: list[str] = []
        original = preprocessor.normalize

        def record_normalized(text: str) -> str:
            result = original(text)
            normalized.append(result)
            return result

        monkeypatch.setattr(preprocessor, 'normalize', record_normalized)
        retrieve_index(
            index, boundary_query('  Não   quero\nfront-end,  prefiro APIs ')
        )
        assert normalized[0] == 'Não quero front-end, prefiro APIs'

    def test_should_fall_back_to_the_semantic_ranking_for_a_stop_word_query(
        self, index: BoundaryIndex
    ) -> None:
        ranking = retrieve_index(index, boundary_query('Eu quero isso e aquilo'))

        assert ranking.lexical_ranking == ()
        assert ranking.semantic_ranking
        assert all(entry.lexical_rank is None for entry in ranking.entries)

    def test_should_fuse_lexical_and_semantic_rankings_by_reciprocal_rank(
        self, index: BoundaryIndex
    ) -> None:
        manifest = index.resources.manifest
        ranking = retrieve_index(
            index,
            boundary_query(
                'Quero construir interfaces com componentes e estado usando React'
            ),
        )

        assert ranking.index_version == index.version
        assert 0 < len(ranking.lexical_ranking) <= manifest.lexical_limit
        assert 0 < len(ranking.semantic_ranking) <= manifest.semantic_limit
        assert len(ranking.entries) <= manifest.candidate_limit
        expected: dict[str, float] = {}
        for source in (ranking.lexical_ranking, ranking.semantic_ranking):
            for rank, skill_id in enumerate(source, 1):
                expected[skill_id] = expected.get(skill_id, 0.0) + 1 / (
                    manifest.rrf_k + rank
                )
        assert [entry.skill_id for entry in ranking.entries] == sorted(
            expected, key=lambda skill_id: (-expected[skill_id], skill_id)
        )
        for entry in ranking.entries:
            assert entry.score == pytest.approx(expected[entry.skill_id])
            assert entry.lexical_rank == (
                ranking.lexical_ranking.index(entry.skill_id) + 1
                if entry.skill_id in ranking.lexical_ranking
                else None
            )
            assert entry.semantic_rank == (
                ranking.semantic_ranking.index(entry.skill_id) + 1
                if entry.skill_id in ranking.semantic_ranking
                else None
            )
        shared = set(ranking.lexical_ranking) & set(ranking.semantic_ranking)
        assert index.corpus.ids_by_name['React'] in shared
        assert boundary_entry_names(index, ranking)[0] == 'React'

    def test_should_refresh_the_ranking_with_the_full_answer_set(
        self, index: BoundaryIndex
    ) -> None:
        intent = 'Quero aprender a fazer sites'
        alone = retrieve_index(index, boundary_query(intent))
        structure = retrieve_index(
            index,
            boundary_query(
                intent,
                (
                    'Quero começar pela estrutura e pela aparência das páginas',
                    'Ainda não sei programar',
                ),
            ),
        )
        behavior = retrieve_index(
            index,
            boundary_query(
                intent, ('Já sei HTML e CSS', 'Quero interatividade e componentes')
            ),
        )

        assert boundary_entry_names(index, structure)[0] == 'HTML e CSS'
        assert structure.entries != behavior.entries
        assert boundary_entry_names(index, behavior).index(
            'React'
        ) < boundary_entry_names(index, structure).index('React')
        assert alone.lexical_ranking != behavior.lexical_ranking
        assert alone.semantic_ranking != behavior.semantic_ranking

    def test_should_rank_the_requested_skill_above_the_negated_one(
        self, index: BoundaryIndex
    ) -> None:
        names = boundary_entry_names(
            index,
            retrieve_index(
                index,
                boundary_query(
                    'Não quero front-end nem páginas, prefiro APIs e regras de '
                    'negócio no servidor'
                ),
            ),
        )

        assert names[0] == 'APIs web'
        assert names.index('APIs web') < names.index('HTML e CSS')

    def test_should_compose_candidates_with_authorized_catalog_data(
        self, index: BoundaryIndex
    ) -> None:
        retrieval = RetrievePlanningSkillsUseCase(
            index.provider, index.corpus.catalog
        ).execute(
            boundary_query(
                'Quero construir interfaces com componentes e estado usando React'
            )
        )
        react = retrieval.candidates[0]

        assert retrieval.index_version == index.version
        assert react.name == 'React'
        assert react.description == 'Construa interfaces com componentes e estado.'
        assert set(react.foundation_skill_ids) == {
            index.corpus.ids_by_name['JavaScript essencial'],
            index.corpus.ids_by_name['HTML e CSS'],
        }
        assert react.lexical_rank == 1
        assert react.semantic_rank == 1
        assert {candidate.name for candidate in retrieval.candidates} <= set(
            index.corpus.ids_by_name
        )
        assert len({candidate.skill_id for candidate in retrieval.candidates}) == len(
            retrieval.candidates
        )


class TestPlanningIntentClassification:
    def test_should_classify_the_labeled_sets_through_the_decision_contract(
        self,
    ) -> None:
        resources = PlannerResources()
        labeled = [
            (item.text, item.label)
            for item in (
                *resources.intent_evaluation.calibration,
                *resources.intent_evaluation.held_out,
            )
        ]
        double = BoundaryJevDouble(dict(labeled))
        use_case = ClassifyPlanningIntentUseCase(boundary_classifier(double.handler))

        matrix, accuracy, undue_refusals = boundary_evaluate(use_case, labeled)
        boundary_print_matrix('transport double', matrix)
        result = use_case.execute(
            PlanningQuery(intent=labeled[0][0], answers=('Nunca programei',))
        )

        assert accuracy == 1.0
        assert undue_refusals == 0
        assert len(double.requests) == len(labeled) + 1
        assert double.requests[-1]['state'] == {
            'intent': labeled[0][0],
            'answers': ['Nunca programei'],
        }
        assert [label for label, _ in result.probabilities] == [
            'ambiguous',
            'learning',
            'out-of-scope',
        ]
        assert [value for _, value in result.probabilities] == pytest.approx(
            [0.05, 0.9, 0.05]
        )

    @pytest.mark.parametrize(
        ('choice', 'confidence', 'expected'),
        [
            ('learning', 0.95, PlanningIntentKind.LEARNING),
            ('learning', 0.4, PlanningIntentKind.AMBIGUOUS),
            ('out-of-scope', 0.95, PlanningIntentKind.OUT_OF_SCOPE),
            ('out-of-scope', 0.5, PlanningIntentKind.AMBIGUOUS),
            ('ambiguous', 0.34, PlanningIntentKind.AMBIGUOUS),
        ],
    )
    def test_should_downgrade_low_confidence_decisions_to_clarification(
        self, choice: str, confidence: float, expected: PlanningIntentKind
    ) -> None:
        classification = ClassifyPlanningIntentUseCase(
            boundary_classifier(lambda _request: boundary_decision(choice, confidence))
        ).execute(boundary_query('Quero evoluir'))

        assert classification.kind is expected
        assert classification.confidence == confidence

    def test_should_recover_from_one_retryable_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(jev_module, 'sleep', boundary_no_sleep)
        statuses = iter((503, 200))

        def handler(_request: httpx.Request) -> httpx.Response:
            status = next(statuses)
            return (
                boundary_decision('learning', 0.9)
                if status == 200
                else httpx.Response(status, json={'error': 'busy'})
            )

        classification = ClassifyPlanningIntentUseCase(
            boundary_classifier(handler)
        ).execute(boundary_query('Quero aprender React'))

        assert classification.kind is PlanningIntentKind.LEARNING
        assert next(statuses, None) is None

    @pytest.mark.parametrize(
        ('name', 'respond', 'expected_requests'),
        [
            ('retryable exhausted', lambda: httpx.Response(503, json={}), 3),
            ('bad request', lambda: httpx.Response(400, json={}), 1),
            ('not json', lambda: httpx.Response(200, text='not json'), 1),
            ('missing answer', lambda: httpx.Response(200, json={'answers': {}}), 1),
            ('choice outside the set', lambda: boundary_decision('maybe', 0.9), 1),
            (
                'probabilities outside the set',
                lambda: httpx.Response(
                    200,
                    json={
                        'answers': {
                            'planning_intent': {
                                'type': 'choice',
                                'choice': 'learning',
                                'confidence': 0.9,
                                'probabilities': {'learning': 0.9, 'other': 0.1},
                            }
                        }
                    },
                ),
                1,
            ),
            (
                'probabilities not summing to one',
                lambda: httpx.Response(
                    200,
                    json={
                        'answers': {
                            'planning_intent': {
                                'type': 'choice',
                                'choice': 'learning',
                                'confidence': 0.9,
                                'probabilities': {
                                    'learning': 0.9,
                                    'out-of-scope': 0.9,
                                    'ambiguous': 0.9,
                                },
                            }
                        }
                    },
                ),
                1,
            ),
        ],
    )
    def test_should_raise_the_typed_error_instead_of_a_refusal_on_technical_failures(
        self,
        monkeypatch: pytest.MonkeyPatch,
        name: str,
        respond: Callable[[], httpx.Response],
        expected_requests: int,
    ) -> None:
        del name
        monkeypatch.setattr(jev_module, 'sleep', boundary_no_sleep)
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return respond()

        with pytest.raises(PlanningClassificationUnavailableError):
            ClassifyPlanningIntentUseCase(boundary_classifier(handler)).execute(
                boundary_query('Quero aprender React')
            )
        assert len(requests) == expected_requests

    def test_should_retry_transport_errors_before_failing_closed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(jev_module, 'sleep', boundary_no_sleep)
        attempts: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            attempts.append(request)
            raise httpx.ConnectError('down', request=request)

        with pytest.raises(PlanningClassificationUnavailableError):
            ClassifyPlanningIntentUseCase(boundary_classifier(handler)).execute(
                boundary_query('Quero aprender React')
            )
        assert len(attempts) == 3

    def test_should_fail_closed_without_an_api_key(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return boundary_decision('learning', 0.9)

        with pytest.raises(PlanningClassificationUnavailableError):
            ClassifyPlanningIntentUseCase(
                boundary_classifier(handler, api_key=None)
            ).execute(boundary_query('Quero aprender'))
        assert requests == []

    def test_should_reject_thresholds_outside_the_closed_set(self) -> None:
        """Defensive constructor configuration only; no classification executes."""
        with httpx.Client() as client, pytest.raises(ValueError, match='thresholds'):
            JevPlanningIntentClassifierProvider(
                client,
                'test-key',
                BOUNDARY_DECISIONS_URL,
                BOUNDARY_MODEL,
                {'learning': 0.5},
            )

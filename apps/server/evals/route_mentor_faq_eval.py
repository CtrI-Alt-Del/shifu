from __future__ import annotations

from contextlib import nullcontext
import hashlib
from importlib.resources import files
import json
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from shifu.intelligence.ai.data.mentor_resources import MentorResources
from shifu.intelligence.core.domain.enums.mentor_intent import MentorIntent
from shifu.intelligence.prepare_mentor_indexes import prepare_indexes
from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
    SentenceTransformersEmbeddingsProvider,
)
from shifu.intelligence.providers.retrieval.sentence_transformers.sentence_transformers_mentor_faq_reranker_provider import (
    SentenceTransformersMentorFaqRerankerProvider,
)
from shifu.intelligence.providers.routing.local.local_mentor_route_provider import (
    LocalMentorRouteProvider,
)
from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
    SpacyMentorTextPreprocessorProvider,
)
from shifu.shared.core.domain.structures.mentor_catalog_entry import (
    MentorCatalogEntry,
)
from shifu.shared.core.domain.structures.mentor_context_snapshot import (
    MentorContextSnapshot,
)

from evals.classify_mentor_intent_eval import InMemoryMentorEmbeddingsRepository
from evals.eval import Eval

if TYPE_CHECKING:
    from collections.abc import Mapping
    from contextlib import AbstractContextManager

    from shifu.intelligence.core.domain.enums import MentorSummaryFailureCode
    from shifu.intelligence.core.domain.structures import MentorReviewResult
    from shifu.intelligence.core.domain.structures.mentor_route_result import (
        MentorRouteResult,
    )


def _skill(reference_id: str, title: str, description: str) -> MentorCatalogEntry:
    return MentorCatalogEntry(
        reference_id=reference_id,
        kind='skill',
        skill_id=reference_id,
        competency_id=None,
        title=title,
        description=description,
        concept_ids=(),
        source_version='curriculum-projection-v1',
    )


class _SyntheticMentorCatalogProvider:
    """A small synthetic Curriculum, shaped like the development seed."""

    ENTRIES: ClassVar[tuple[MentorCatalogEntry, ...]] = (
        _skill(
            'skill-react',
            'React',
            'Componentes, estado e propriedades para construir interfaces web.',
        ),
        _skill(
            'skill-web-apis',
            'APIs web',
            'Requisições HTTP, métodos e respostas JSON entre cliente e servidor.',
        ),
        _skill(
            'skill-html-css',
            'HTML e CSS',
            'Estrutura de páginas com HTML e estilos visuais com CSS.',
        ),
        _skill(
            'skill-javascript',
            'JavaScript essencial',
            'Variáveis, funções e eventos na linguagem JavaScript.',
        ),
        _skill(
            'skill-programming-logic',
            'Lógica de programação',
            'Sequência, condições e repetição para resolver problemas.',
        ),
        _skill(
            'skill-algorithm-decisions',
            'Decisões em algoritmos',
            'Condições e caminhos de decisão em algoritmos.',
        ),
        _skill(
            'skill-adaptive-lab',
            'Laboratório de decisões adaptativas',
            'Prática com cenários que exigem escolher entre caminhos.',
        ),
    )

    def read_projection(self) -> tuple[MentorCatalogEntry, ...]:
        return self.ENTRIES

    def is_diagnostic_activity(
        self, skill_id: str, competency_id: str | None, activity_id: str
    ) -> bool:
        return False

    def search(
        self, account_id: str, query: str, eligible_references: tuple[str, ...]
    ) -> tuple[MentorCatalogEntry, ...]:
        return ()


class _SilentMentorTelemetryProvider:
    """The route's telemetry stages, recorded nowhere."""

    def scope(self, stage: str) -> AbstractContextManager[None]:
        return nullcontext()

    def record_inference(
        self,
        profile: str,
        used_tokens: int | None,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_usd: float | None,
    ) -> None:
        return None

    def record_answer(
        self,
        *,
        attempt_id: str,
        block_key: str,
        version: int,
        correlation_id: str,
        answer: str,
    ) -> None:
        return None

    def record_review(
        self,
        *,
        attempt_id: str,
        block_key: str,
        version: int,
        correlation_id: str,
        answer: str,
        review: MentorReviewResult,
    ) -> None:
        return None

    def emit(
        self,
        stage: str,
        *,
        correlation_id: str,
        profile: str,
        duration_ms: float,
        counts: Mapping[str, int],
        outcome: Literal[
            'passed', 'failed', 'abstained', 'cancelled', 'ready', 'discarded'
        ],
        failure_code: MentorSummaryFailureCode | None = None,
    ) -> None:
        return None


class RouteMentorFaqEval(Eval):
    """Gate the local Mentor route on FAQ answers and Curriculum proposals.

    Runs the real `LocalMentorRouteProvider` with the pinned E5 embeddings, the FAQ
    cross-encoder and spaCy, over an in-memory index of the Mentor corpus and a
    synthetic Curriculum. FAQ cases come from `mentor-evaluation.json`: a labeled
    question must be answered by its FAQ entry or left unanswered, never by another
    one, and a comparison of two Shifu terms must receive both entries. Curriculum
    cases check that only entries sharing a term with the message are proposed.
    No database and no remote model: identical in double and real modes.
    """

    selector = 'route-mentor-faq'
    workflow_id = 'intelligence-route-mentor-faq'
    prompt_revision = 'e5-small-bm25-rerank-tie-v3'
    unavailable_failure_code = 'route_unavailable'
    LABELED_SECTIONS: ClassVar[tuple[str, ...]] = (
        'calibration',
        'held_out',
        'pipeline_held_out',
    )
    NO_WRONG_ANSWER_CASE: ClassVar[str] = 'faq_no_wrong_answer'
    CURRICULUM_CASES: ClassVar[tuple[tuple[str, str, str | None], ...]] = (
        (
            'curriculum_ignores_unrelated_question',
            (
                'Oi boa noite eu queria saber qual é a diferença entre habilidade e '
                'competência dentro da plataforma do shifu'
            ),
            None,
        ),
        ('curriculum_proposes_named_skill', 'Quero aprender React', 'skill-react'),
        (
            'curriculum_proposes_skill_by_subject',
            'Existe alguma habilidade de HTML?',
            'skill-html-css',
        ),
        (
            'curriculum_ignores_generic_question',
            'Qual é a capital da França?',
            None,
        ),
    )

    def __init__(self, *, mode: str) -> None:
        super().__init__(mode=mode)
        self.model_profile = 'local-e5-small-bm25-cross-encoder'
        self._router: LocalMentorRouteProvider | None = None
        self._answers: dict[str, str] = {}

    @property
    def dataset_revision(self) -> str:
        sections = self.evaluation()
        digest = hashlib.sha256(
            json.dumps(
                {
                    name: sections[name]
                    for name in (*self.LABELED_SECTIONS, 'faq_regression')
                },
                sort_keys=True,
                ensure_ascii=False,
                separators=(',', ':'),
            ).encode()
        ).hexdigest()
        return f'mentor-faq-synthetic-{digest[:12]}'

    @staticmethod
    def evaluation() -> dict[str, Any]:
        package = files('shifu.intelligence.ai.data')
        return json.loads(
            package.joinpath('mentor-evaluation.json').read_text(encoding='utf-8')
        )

    # --- cases ---------------------------------------------------------------

    def cases(self) -> tuple[Eval.LocalCase, ...]:
        evaluation = self.evaluation()
        labeled = tuple(
            (entry['text'], entry.get('answer_id'))
            for section in self.LABELED_SECTIONS
            for entry in evaluation[section]
        )
        return (
            Eval.LocalCase(
                name=self.NO_WRONG_ANSWER_CASE,
                tags=('faq', 'precision'),
                input=labeled,
                expected={'max_wrong_answers': 0},
            ),
            *(
                Eval.LocalCase(
                    name=f'faq_comparison_regression_{index}',
                    tags=('faq', 'regression'),
                    input=entry['text'],
                    expected=tuple(sorted(entry['answer_ids'])),
                )
                for index, entry in enumerate(evaluation['faq_regression'], start=1)
            ),
            *(
                Eval.LocalCase(
                    name=name,
                    tags=('curriculum', 'regression'),
                    input=text,
                    expected=reference,
                )
                for name, text, reference in self.CURRICULUM_CASES
            ),
        )

    # --- execution -----------------------------------------------------------

    def run_case(self, case: Eval.LocalCase) -> Eval.CaseOutcome:
        if case.name == self.NO_WRONG_ANSWER_CASE:
            return self.score_labeled(case.input)
        route = self.route(case.input)
        if 'curriculum' in case.tags:
            proposed = route.proposed_reference_ids
            passed = (
                proposed == ()
                if case.expected is None
                else bool(proposed) and proposed[0] == case.expected
            )
            return self.CaseOutcome(
                passed,
                None if passed else 'curriculum_proposal_mismatch',
                {'proposed': list(proposed)},
            )
        answered = self.answered(route)
        catalog = any(
            block.intent is MentorIntent.SEARCH_CURRICULUM
            for block in route.local_blocks
        )
        passed = tuple(sorted(answered)) == case.expected and not catalog
        return self.CaseOutcome(
            passed,
            None if passed else 'faq_answer_mismatch',
            {'answered': sorted(answered), 'catalog_block': catalog},
        )

    def score_labeled(
        self, labeled: tuple[tuple[str, str | None], ...]
    ) -> Eval.CaseOutcome:
        correct = abstained = 0
        wrong: list[dict[str, Any]] = []
        # A tie may publish a related entry next to the expected one: reported, not
        # failed, because the expected answer still reaches the learner.
        with_extra: list[dict[str, Any]] = []
        for text, expected in labeled:
            answered = self.answered(self.route(text))
            outcome = {'text': text, 'expected': expected, 'answered': sorted(answered)}
            if not answered:
                abstained += 1
            elif expected not in answered:
                wrong.append(outcome)
            else:
                correct += 1
                if len(answered) > 1:
                    with_extra.append(outcome)
        passed = not wrong
        return self.CaseOutcome(
            passed,
            None if passed else 'faq_wrong_answer',
            {
                'support': len(labeled),
                'correct': correct,
                'abstained': abstained,
                'wrong': wrong,
                'correct_with_extra_answer': with_extra,
            },
        )

    def answered(self, route: MentorRouteResult) -> set[str]:
        """The FAQ entries whose answer text the route published."""
        return {
            self._answers[block.content]
            for block in route.local_blocks
            if block.content in self._answers
        }

    def route(self, text: str) -> MentorRouteResult:
        router = self.router()
        return router.route(
            text,
            MentorContextSnapshot(
                goal_id=None,
                skill_experience_id=None,
                skill_id=None,
                competency_id=None,
                activity_id=None,
                skill_completed=None,
                diagnostic_in_progress=False,
                facts=(),
                eligible_references=tuple(
                    entry.reference_id
                    for entry in _SyntheticMentorCatalogProvider.ENTRIES
                ),
                resolved_references=(),
                unavailable_sources=(),
            ),
        )

    def router(self) -> LocalMentorRouteProvider:
        if self._router is None:
            resources = MentorResources()
            embeddings = SentenceTransformersEmbeddingsProvider()
            repository = InMemoryMentorEmbeddingsRepository()
            catalog = _SyntheticMentorCatalogProvider()
            prepare_indexes(embeddings, repository, catalog, resources)
            self._answers = {answer.answer: answer.id for answer in resources.answers}
            self._router = LocalMentorRouteProvider(
                embeddings,
                repository,
                SpacyMentorTextPreprocessorProvider(),
                resources,
                telemetry=_SilentMentorTelemetryProvider(),
                catalog_provider=catalog,
                reranker_provider=SentenceTransformersMentorFaqRerankerProvider(),
            )
        return self._router

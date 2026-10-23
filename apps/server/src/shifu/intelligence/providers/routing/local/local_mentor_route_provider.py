import hashlib
import re
from time import perf_counter
from uuid import uuid4
from typing import ClassVar

from shifu.intelligence.ai.data.mentor_resources import MentorResources
from shifu.intelligence.core.domain.enums.mentor_intent import MentorIntent
from shifu.intelligence.core.domain.structures.mentor_intent_match import (
    MentorIntentMatch,
)
from shifu.intelligence.core.domain.structures.mentor_response_block import (
    MentorResponseBlock,
)
from shifu.intelligence.core.domain.structures.mentor_route_result import (
    MentorRouteResult,
)
from shifu.intelligence.core.interfaces.mentor_embeddings_provider import (
    MentorEmbeddingsProvider,
)
from shifu.intelligence.core.interfaces.mentor_embeddings_repository import (
    MentorEmbeddingsRepository,
)
from shifu.intelligence.core.interfaces.mentor_faq_reranker_provider import (
    MentorFaqRerankerProvider,
)
from shifu.intelligence.core.interfaces.mentor_telemetry_provider import (
    MentorTelemetryProvider,
)
from shifu.intelligence.providers.intent_classification.embeddings.embeddings_mentor_intent_classifier_provider import (
    EmbeddingsMentorIntentClassifierProvider,
)
from shifu.intelligence.providers.retrieval.bm25.bm25_mentor_hybrid_retrieval_provider import (
    Bm25MentorHybridRetrievalProvider,
)
from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
    SpacyMentorTextPreprocessorProvider,
)
from shifu.intelligence.providers.telemetry.langfuse.langfuse_mentor_telemetry_provider import (
    LangfuseMentorTelemetryProvider,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures.mentor_context_snapshot import (
    MentorContextSnapshot,
)
from shifu.shared.core.interfaces.mentor_catalog_provider import MentorCatalogProvider


class LocalMentorRouteProvider:
    _NEUTRAL_PREFIX: ClassVar[re.Pattern[str]] = re.compile(
        r'^\s*(?:(?:oi|ol[aá]|bom dia|boa tarde|boa noite)\b[\s,!:.]+|'
        r'(?:eu\s+)?tenho\s+(?:uma\s+)?d[uú]vida\s*[,!:]\s*)(?=\S)',
        re.IGNORECASE,
    )
    _ELLIPTICAL_MAX_CONTENT_TOKENS: ClassVar[int] = 6
    _EXPANSION_TOPIC_LIMIT: ClassVar[int] = 3
    _FACTS: ClassVar[dict[MentorIntent, tuple[tuple[str, str], ...]]] = {
        MentorIntent.CONSULT_PROGRESS: (
            ('progress_summary', 'Progresso'),
            ('completed_skills', 'Habilidades concluídas'),
        ),
        MentorIntent.CONSULT_GAMIFICATION: (
            ('xp', 'XP'),
            ('level', 'Nível'),
            ('streak', 'Sequência'),
            ('achievements', 'Conquistas'),
        ),
        MentorIntent.EXPLAIN_ASSESSMENT: (('assessment_summary', 'Avaliação oficial'),),
        MentorIntent.FIND_MATERIALS_ACTIVITIES: (
            ('eligible_materials', 'Materiais disponíveis'),
            ('activities', 'Atividades disponíveis'),
        ),
    }
    _embeddings: MentorEmbeddingsProvider
    _resources: MentorResources
    _classifier: EmbeddingsMentorIntentClassifierProvider
    _retrieval: Bm25MentorHybridRetrievalProvider
    _telemetry: MentorTelemetryProvider
    _catalog: MentorCatalogProvider | None
    _preprocessor: SpacyMentorTextPreprocessorProvider

    def __init__(
        self,
        embeddings: MentorEmbeddingsProvider,
        repository: MentorEmbeddingsRepository,
        preprocessor: SpacyMentorTextPreprocessorProvider,
        resources: MentorResources,
        telemetry: MentorTelemetryProvider | None = None,
        catalog_provider: MentorCatalogProvider | None = None,
        reranker_provider: MentorFaqRerankerProvider | None = None,
    ) -> None:
        self._catalog = catalog_provider
        self._preprocessor = preprocessor
        self._telemetry = telemetry or LangfuseMentorTelemetryProvider()
        self._embeddings = embeddings
        self._resources = resources
        self._classifier = EmbeddingsMentorIntentClassifierProvider(
            repository, resources
        )
        self._retrieval = Bm25MentorHybridRetrievalProvider(
            repository, preprocessor, resources, reranker_provider
        )

    def route(
        self,
        content: str,
        context: MentorContextSnapshot,
        topics: tuple[str, ...] = (),
    ) -> MentorRouteResult:
        started = perf_counter()
        matches, answer_ids, generation, unanswered, block_matches, expanded = (
            self._semantic(content, topics)
        )
        proposed: tuple[str, ...] = ()
        if self._catalog is not None and context.eligible_references:
            try:
                with self._telemetry.scope('retrieve'):
                    vector = self._embeddings.embed_queries((content,))[0]
                    proposed = self._retrieval.retrieve_curriculum(
                        content,
                        vector,
                        self._catalog.read_projection(),
                        context.eligible_references,
                    )
            except ServiceUnavailableError:
                proposed = ()
        blocks = self._local_blocks(block_matches, answer_ids, context)
        clarification = None
        if (
            any(
                intent in block_matches
                for intent in (
                    MentorIntent.REQUEST_HINT,
                    MentorIntent.EXPLAIN_ASSESSMENT,
                )
            )
            and context.goal_id is None
        ):
            clarification = 'Qual Objetivo e Habilidade você quer consultar?'
            generation = ()
            unanswered = ()
        if generation or (not blocks and clarification is None):
            blocks.append(
                MentorResponseBlock(
                    block_key=hashlib.sha256(b'local-abstention').hexdigest()[:32],
                    ordinal=len(blocks),
                    intent=None,
                    content=(
                        'Ainda não encontrei uma resposta local confiável para essa '
                        'pergunta. Tente perguntar sobre um Objetivo, uma Habilidade, '
                        'seu progresso ou um conteúdo do Currículo.'
                    ),
                )
            )
        self._telemetry.emit(
            'route',
            correlation_id=str(uuid4()),
            profile='local',
            duration_ms=(perf_counter() - started) * 1000,
            counts={'blocks': len(blocks), 'expanded': expanded},
            outcome='passed',
        )
        return MentorRouteResult(
            intents=tuple(matches.values()),
            local_blocks=tuple(blocks),
            generation_requests=generation,
            clarification=clarification,
            proposed_reference_ids=proposed,
            unanswered_requests=unanswered,
        )

    def _semantic(
        self, content: str, topics: tuple[str, ...]
    ) -> tuple[
        dict[MentorIntent, MentorIntentMatch],
        list[str],
        tuple[str, ...],
        tuple[str, ...],
        dict[MentorIntent, MentorIntentMatch],
        int,
    ]:
        parts = self._parts(content)
        matches: dict[MentorIntent, MentorIntentMatch] = {}
        answer_ids: list[str] = []
        generation: list[str] = []
        unanswered: list[str] = []
        block_matches: dict[MentorIntent, MentorIntentMatch] = {}
        expanded = 0
        try:
            with self._telemetry.scope('classify'):
                vectors = self._embeddings.embed_queries(
                    tuple(self._semantic_query(text) for text in (content, *parts))
                )
                classified = tuple(
                    self._classifier.classify(vector) for vector in vectors
                )
            for labels in classified:
                self._merge_matches(matches, labels)
            for part, vector, labels in zip(
                parts, vectors[1:], classified[1:], strict=True
            ):
                if self._preprocessor.is_negated_request(part):
                    continue
                with self._telemetry.scope('retrieve'):
                    references = self._retrieval.retrieve(
                        self._semantic_query(part), vector
                    )
                    if not references and topics and self._is_elliptical(part):
                        # One guarded retry; the retrieval gates are unchanged.
                        expanded += 1
                        references = self._retrieve_with_topics(part, vector, topics)
                answer_ids.extend(references)
                if not references:
                    self._merge_matches(block_matches, labels)
                if self._requires_generation(labels, references):
                    generation.append(part)
                    if not references:
                        unanswered.append(part)
        except ServiceUnavailableError:
            return {}, [], (content,), (content,), {}, expanded
        return (
            matches,
            list(dict.fromkeys(answer_ids)),
            tuple(dict.fromkeys(generation)),
            tuple(dict.fromkeys(unanswered)),
            block_matches,
            expanded,
        )

    def _is_elliptical(self, part: str) -> bool:
        return (
            len(self._preprocessor.tokenize(part))
            <= self._ELLIPTICAL_MAX_CONTENT_TOKENS
            or self._preprocessor.has_unresolved_reference(part)
        )

    def _retrieve_with_topics(
        self,
        part: str,
        part_vector: tuple[float, ...],
        topics: tuple[str, ...],
    ) -> tuple[str, ...]:
        unique_topics = tuple(dict.fromkeys(topic for topic in topics if topic.strip()))
        if not unique_topics:
            return ()
        topic_vectors = self._embeddings.embed_passages(unique_topics)
        ranked = sorted(
            range(len(unique_topics)),
            key=lambda index: (
                -sum(
                    left * right
                    for left, right in zip(
                        part_vector, topic_vectors[index], strict=True
                    )
                ),
                index,
            ),
        )[: self._EXPANSION_TOPIC_LIMIT]
        expanded_part = ' '.join((part, *(unique_topics[index] for index in ranked)))
        expanded_vector = self._embeddings.embed_queries(
            (self._semantic_query(expanded_part),)
        )[0]
        return self._retrieval.retrieve(
            self._semantic_query(expanded_part), expanded_vector
        )

    @staticmethod
    def _merge_matches(
        matches: dict[MentorIntent, MentorIntentMatch],
        labels: tuple[MentorIntentMatch, ...],
    ) -> None:
        for match in labels:
            existing = matches.get(match.intent)
            if existing is None or match.similarity > existing.similarity:
                matches[match.intent] = match

    @staticmethod
    def _semantic_query(content: str) -> str:
        query = content
        while True:
            normalized = LocalMentorRouteProvider._NEUTRAL_PREFIX.sub(
                '', query, count=1
            )
            if normalized == query:
                # Removing an introduction exposes a new sentence boundary.
                return query[0].upper() + query[1:] if query != content else query
            query = normalized

    @staticmethod
    def _parts(content: str) -> tuple[str, ...]:
        return tuple(
            part.strip()
            for part in re.split(
                r'\?|;|\n|\be também\b|\balém disso\b', content, flags=re.IGNORECASE
            )
            if part.strip()
        ) or (content,)

    def _requires_generation(
        self, labels: tuple[MentorIntentMatch, ...], answers: tuple[str, ...]
    ) -> bool:
        generative = {MentorIntent.REQUEST_HINT, MentorIntent.LEARNING_CONVERSATION}
        if any(match.intent in generative for match in labels):
            return True
        if answers:
            return False
        return not labels or any(
            match.intent not in self._FACTS
            and match.intent != MentorIntent.SEARCH_CURRICULUM
            for match in labels
        )

    def _local_blocks(
        self,
        matches: dict[MentorIntent, MentorIntentMatch],
        answer_ids: list[str],
        context: MentorContextSnapshot,
    ) -> list[MentorResponseBlock]:
        blocks: list[MentorResponseBlock] = []
        for reference in answer_ids:
            answer = next(
                answer for answer in self._resources.answers if answer.id == reference
            )
            blocks.append(
                self._block(
                    f'faq:{reference}',
                    answer.answer,
                    len(blocks),
                    MentorIntent.EXPLAIN_CONCEPT,
                )
            )
        grouped: dict[str, list[str]] = {}
        for key, value in context.facts:
            grouped.setdefault(key, []).append(value)
        facts = {key: '\n'.join(values) for key, values in grouped.items()}
        strongest_answered = self._strongest_answered_fact(matches, grouped, facts)
        for intent in MentorIntent:
            if intent not in matches:
                continue
            fields = self._FACTS.get(intent)
            if fields is not None:
                progress = (
                    self._progress_text(grouped)
                    if intent == MentorIntent.CONSULT_PROGRESS
                    else None
                )
                if (
                    progress is None
                    and not any(key in facts for key, _ in fields)
                    and matches[intent].similarity < strongest_answered
                ):
                    # A weaker match without facts is noise next to a real answer.
                    continue
                text = progress or self._fact_text(fields, facts)
                blocks.append(
                    self._block(f'fact:{intent.value}', text, len(blocks), intent)
                )
            elif intent == MentorIntent.SEARCH_CURRICULUM:
                text = facts.get(
                    'catalog_summary',
                    'Preciso de mais detalhes sobre a Habilidade que você procura.',
                )
                blocks.append(self._block('catalog', text, len(blocks), intent))
        return blocks

    def _strongest_answered_fact(
        self,
        matches: dict[MentorIntent, MentorIntentMatch],
        grouped: dict[str, list[str]],
        facts: dict[str, str],
    ) -> float:
        """Similarity of the best matched fact intent that has facts to render."""
        scores = [
            match.similarity
            for intent, match in matches.items()
            if (fields := self._FACTS.get(intent)) is not None
            and (
                (
                    intent == MentorIntent.CONSULT_PROGRESS
                    and self._progress_text(grouped) is not None
                )
                or any(key in facts for key, _ in fields)
            )
        ]
        return max(scores, default=-1.0)

    @staticmethod
    def _fact_text(fields: tuple[tuple[str, str], ...], facts: dict[str, str]) -> str:
        available = [f'{label}: {facts[key]}' for key, label in fields if key in facts]
        return (
            '\n\n'.join(available)
            if available
            else 'Essas informações estão indisponíveis no momento.'
        )

    @staticmethod
    def _progress_text(grouped: dict[str, list[str]]) -> str | None:
        """Render the overview facts; None keeps the selected-Habilidade rendering."""
        if not any(
            key in grouped for key in ('goals', 'progress_summary', 'completed_skills')
        ):
            return 'Você ainda não tem Objetivos. Crie um na tela inicial para acompanhar seu progresso.'
        if 'goal_skill_status' in grouped:
            title = grouped['goal_progress_title'][0]
            bullets = '\n'.join(f'- {value}' for value in grouped['goal_skill_status'])
            return f'Progresso no Objetivo {title}:\n{bullets}'
        if 'progress_overview' not in grouped:
            return None
        bullets = '\n'.join(f'- {value}' for value in grouped['progress_overview'])
        sections = [f'Progresso:\n{bullets}']
        if 'completed_skills' in grouped:
            completed = '\n'.join(grouped['completed_skills'])
            sections.append(f'Habilidades concluídas: {completed}')
        sections.append('Diga o nome de um Objetivo para ver as Habilidades dele.')
        return '\n\n'.join(sections)

    @staticmethod
    def _block(
        key: str, content: str, ordinal: int, intent: MentorIntent
    ) -> MentorResponseBlock:
        return MentorResponseBlock(
            block_key=hashlib.sha256(key.encode()).hexdigest()[:32],
            ordinal=ordinal,
            intent=intent,
            content=content,
        )

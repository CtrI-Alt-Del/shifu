from typing import Any
from unittest.mock import Mock, create_autospec

import pytest

from shifu.intelligence.ai.data.mentor_resources import MentorResources
from shifu.intelligence.core.domain.enums.mentor_intent import MentorIntent
from shifu.intelligence.core.domain.structures.mentor_intent_match import (
    MentorIntentMatch,
)
from shifu.intelligence.core.interfaces.mentor_embeddings_provider import (
    MentorEmbeddingsProvider,
)
from shifu.intelligence.core.interfaces.mentor_embeddings_repository import (
    MentorEmbeddingsRepository,
)
from shifu.intelligence.core.interfaces.mentor_telemetry_provider import (
    MentorTelemetryProvider,
)
from shifu.intelligence.providers.routing.local import local_mentor_route_provider
from shifu.intelligence.providers.routing.local.local_mentor_route_provider import (
    LocalMentorRouteProvider,
)
from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
    SpacyMentorTextPreprocessorProvider,
)
from tests.intelligence.core.use_cases.mentor_response_phase_test_setup import (
    context_snapshot,
)

_ACTIVITY = '01SHFCK0000000000000000112'
_FACTS = (
    ('activities', f'{_ACTIVITY}: Cebola e legumes'),
    ('assessment_summary', 'Cebola e legumes: nota oficial 62.00'),
)
_QUESTION = (('activity_questions', 'heat: questão 1 de 1 (escolha única): Fogo?'),)


def _match(intent: MentorIntent) -> MentorIntentMatch:
    return MentorIntentMatch(intent=intent, similarity=0.9)


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> LocalMentorRouteProvider:
    # Retrieval is not exercised: routing is classified directly below.
    monkeypatch.setattr(
        local_mentor_route_provider, 'Bm25MentorHybridRetrievalProvider', Mock()
    )
    return LocalMentorRouteProvider(
        create_autospec(MentorEmbeddingsProvider, instance=True),
        create_autospec(MentorEmbeddingsRepository, instance=True),
        create_autospec(SpacyMentorTextPreprocessorProvider, instance=True),
        MentorResources(),
        create_autospec(MentorTelemetryProvider, instance=True),
    )


def _classify(
    monkeypatch: pytest.MonkeyPatch,
    provider: LocalMentorRouteProvider,
    intents: tuple[MentorIntent, ...],
    generation: tuple[str, ...] = (),
) -> None:
    matches = {intent: _match(intent) for intent in intents}
    answer_ids: list[str] = []

    def semantic(*_: Any) -> tuple[object, ...]:
        return (matches, answer_ids, generation, generation, matches, 0, False)

    monkeypatch.setattr(provider, '_semantic', semantic)


class TestLocalMentorRouteProviderScreenQuestion:
    def test_should_answer_a_hint_without_the_material_and_grade_lists(
        self, monkeypatch: pytest.MonkeyPatch, provider: LocalMentorRouteProvider
    ) -> None:
        content = 'Me dá uma dica para esta questão?'
        _classify(
            monkeypatch,
            provider,
            (
                MentorIntent.REQUEST_HINT,
                MentorIntent.FIND_MATERIALS_ACTIVITIES,
                MentorIntent.EXPLAIN_ASSESSMENT,
            ),
            (content,),
        )

        result = provider.route(content, context_snapshot(goal_id='goal', facts=_FACTS))

        assert [block.intent for block in result.local_blocks] == [None]
        assert result.generation_requests == (content,)

    def test_should_send_a_question_about_the_screen_to_the_writer(
        self, monkeypatch: pytest.MonkeyPatch, provider: LocalMentorRouteProvider
    ) -> None:
        content = 'Não entendi o enunciado'
        _classify(monkeypatch, provider, (MentorIntent.EXPLAIN_ASSESSMENT,))

        result = provider.route(
            content, context_snapshot(goal_id='goal', facts=_FACTS + _QUESTION)
        )

        assert [block.intent for block in result.local_blocks] == [None]
        assert result.generation_requests == (content,)
        assert result.unanswered_requests == (content,)

    def test_should_keep_lists_without_ids_when_the_learner_asks_for_them(
        self, monkeypatch: pytest.MonkeyPatch, provider: LocalMentorRouteProvider
    ) -> None:
        content = 'Quais atividades posso fazer?'
        _classify(monkeypatch, provider, (MentorIntent.FIND_MATERIALS_ACTIVITIES,))

        result = provider.route(
            content, context_snapshot(goal_id='goal', facts=_FACTS + _QUESTION)
        )

        assert [block.content for block in result.local_blocks] == [
            'Atividades disponíveis: Cebola e legumes'
        ]

import pytest

from shifu.intelligence.ai.agno.outputs import MentorAnswerBlockOutput
from shifu.intelligence.core.domain.enums.mentor_intent import MentorIntent
from shifu.intelligence.providers.intent_classification.lexical.lexical_mentor_action_request_provider import (
    LexicalMentorActionRequestProvider,
)

ADD = frozenset({MentorIntent.ADD_SKILL})
REMOVE = frozenset({MentorIntent.REMOVE_SKILL})
NONE: frozenset[MentorIntent] = frozenset()


class TestLexicalMentorActionRequestProvider:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (
                (
                    'Oi boa noite eu queria remover a habilidade chamada react do '
                    'meu objetivo pode ser?'
                ),
                REMOVE,
            ),
            ('Remova React do meu objetivo, por favor!', REMOVE),
            ('Adicione Python ao meu objetivo, ok?', ADD),
            ('Você pode remover a habilidade React?', REMOVE),
            ('Como remover a habilidade React, pode ser?', NONE),
            ('Não remova a habilidade React, pode ser?', NONE),
            ('Qual habilidade devo remover?', NONE),
        ],
    )
    def test_should_keep_a_request_followed_by_a_polite_tag(
        self, text: str, expected: frozenset[MentorIntent]
    ) -> None:
        assert LexicalMentorActionRequestProvider().explicit_intents(text) == expected


class TestMentorAnswerBlockOutput:
    @pytest.mark.parametrize('intent', ['add_skill', 'remove_skill'])
    def test_should_drop_an_action_label_from_a_written_answer(
        self, intent: str
    ) -> None:
        output = MentorAnswerBlockOutput.model_validate_json(
            '{"block_key":"generated-0","ordinal":0,'
            f'"intent":"{intent}","content":"Texto","sources":[]}}'
        )

        assert output.intent is None
        assert output.content == 'Texto'

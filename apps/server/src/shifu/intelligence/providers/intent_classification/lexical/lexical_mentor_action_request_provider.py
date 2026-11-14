import re
import unicodedata
from typing import ClassVar

from shifu.intelligence.core.domain.enums.mentor_intent import MentorIntent


class LexicalMentorActionRequestProvider:
    """Tell whether a learner part explicitly asks to add or remove a Skill.

    Embedding similarity cannot separate "adicione X ao meu Objetivo" from the
    near-misses that share its topic ("quero estudar X", "mostre as Habilidades do
    meu Objetivo"). An action intent therefore also needs plain lexical evidence of a
    request: an imperative or desiderative verb of its direction, naming a Skill or
    an Objective, that is not negated, is not a question or a conditional/purpose
    statement and does not act on the Objective itself. A question mark vetoes the
    sentence unless it is a polite request ("Pode adicionar X ao meu Objetivo?").
    Similarity alone never produces an action.

    The verb, noun and opener lists live only here. They are deliberately not part of
    the Mentor intents resource: they are code-level safety rules, so editing them
    changes neither the resource version hash nor the offline index.
    """

    _ADD_VERB: ClassVar[str] = (
        r'adicion(?:a|am|e|em|ar|o)|acrescent(?:a|am|e|em|ar|o)'
        r'|inclu(?:a|am|i|ir|o)|colo(?:que|quem|ca|car)|insir(?:a|am|o)'
        r'|inser(?:e|ir)|ponha|poe|vincul(?:e|a|ar)'
    )
    _REMOVE_VERB: ClassVar[str] = (
        r'remov(?:a|am|e|em|er|o)|retir(?:e|em|a|ar|o)|tir(?:e|em|a|ar|o)'
        r'|exclu(?:a|am|i|ir|o)|apag(?:ue|uem|a|ar|o)|elimin(?:e|em|a|ar|o)'
        r'|desvincul(?:e|a|ar)|delet(?:e|a|ar)'
    )
    _VERBS: ClassVar[dict[MentorIntent, re.Pattern[str]]] = {
        MentorIntent.ADD_SKILL: re.compile(rf'\b(?:{_ADD_VERB})\b'),
        MentorIntent.REMOVE_SKILL: re.compile(rf'\b(?:{_REMOVE_VERB})\b'),
    }
    # The Objective itself is the object ("exclua meu Objetivo"): not a Skill action.
    _OBJECTIVE_AS_OBJECT: ClassVar[re.Pattern[str]] = re.compile(
        rf'\b(?:{_ADD_VERB}|{_REMOVE_VERB})'
        r'(?:\s+(?:o|os|um|uma|meu|meus|minha|esse|este|todo|todos))*\s+objetivos?\b'
    )
    _DESTINATION: ClassVar[re.Pattern[str]] = re.compile(
        r'\b(?:objetivos?|habilidades?)\b'
    )
    # Questions, permission, purpose and conditional openers: not a request.
    _QUESTION: ClassVar[re.Pattern[str]] = re.compile(
        r'^\s*(?:como|qual|quais|quando|onde|quem|por\s+que|porque|o\s+que'
        r'|quanto|quantos|quantas|posso|da\s+(?:para|pra)|sera\s+que'
        r'|para\s+que|se\s+eu|caso\s+eu'
        r'|(?:quero|queria|gostaria\s+de|preciso)\s+saber\s+se'
        r'|(?:me\s+)?(?:diga|fale|explique))\b'
    )
    _WH_ANYWHERE: ClassVar[re.Pattern[str]] = re.compile(r'\b(?:qual|quais)\b')
    # The only question-mark sentences that remain requests.
    _POLITE_REQUEST: ClassVar[re.Pattern[str]] = re.compile(
        r'^\s*(?:voce\s+)?(?:pode|podes|podem|poderia|consegue|conseguiria)\b'
    )
    _NEGATION: ClassVar[re.Pattern[str]] = re.compile(r'\b(?:nao|nunca|jamais|nem)\b')

    def explicit_intents(self, text: str) -> frozenset[MentorIntent]:
        normalized = self._normalize(text)
        if (
            self._QUESTION.search(normalized)
            or self._WH_ANYWHERE.search(normalized)
            or self._NEGATION.search(normalized)
            or ('?' in normalized and not self._POLITE_REQUEST.search(normalized))
            or not self._DESTINATION.search(normalized)
        ):
            return frozenset()
        if self._OBJECTIVE_AS_OBJECT.search(normalized):
            return frozenset()
        return frozenset(
            intent for intent, verbs in self._VERBS.items() if verbs.search(normalized)
        )

    @staticmethod
    def _normalize(value: str) -> str:
        decomposed = unicodedata.normalize('NFKD', value.casefold())
        return ''.join(char for char in decomposed if not unicodedata.combining(char))

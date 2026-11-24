"""A fictional English Skill whose Learning Activities exercise the language formats.

The Skill reuses the placeholder content that makes any Skill startable and swaps
four of its Learning Activities: word-bank fill-blanks (SHIFU-123), translation
(SHIFU-122), word-translation matching (SHIFU-124) and one Activity with one
question of each format. It is development content for testing those formats, not
official Curriculum.
"""

from dataclasses import dataclass
from hashlib import sha256

from shifu.curriculum.core.domain.entities import (
    Activity,
    Competency,
    Concept,
    Material,
    Skill,
)
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    ChoiceConceptCriterion,
    ChoiceOption,
    CodeConceptCriterion,
    CodeInconclusiveObservation,
    CodeLevelObservation,
    CorrectnessEvaluationPart,
    CurriculumSequence,
    EvaluationRule,
    FillBlanksBankWord,
    FillBlanksBlank,
    FillBlanksConceptCriterion,
    FillBlanksQuestion,
    FillBlanksSegment,
    PairMatchingConceptCriterion,
    PairMatchingItem,
    PairMatchingPair,
    PairMatchingQuestion,
    SingleChoiceQuestion,
    TranslationInconclusiveComment,
    TranslationQuestion,
    TranslationRubricComment,
    TranslationRubricCriterion,
    TranslationRubricEvaluationPart,
)
from shifu.fakers.curriculum.ready_skill_content_faker import ReadySkillContentFaker

ENGLISH_SEED_ID_PREFIX = '01SHFEN'


def english_seed_id(item: int) -> str:
    return f'{ENGLISH_SEED_ID_PREFIX}{item:019d}'


ENGLISH_SKILL_ID = english_seed_id(1)
# Content ids sit at 100 + the item number `ReadySkillContentFaker` assigns.
ENGLISH_COMPETENCY_ID = english_seed_id(101)
ENGLISH_FILL_BLANKS_ACTIVITY_ID = english_seed_id(110)
ENGLISH_TRANSLATION_ACTIVITY_ID = english_seed_id(111)
ENGLISH_PAIR_MATCHING_ACTIVITY_ID = english_seed_id(112)
ENGLISH_MIXED_FORMATS_ACTIVITY_ID = english_seed_id(113)

_CORRECT = 'Correto! Na terceira pessoa do singular, o verbo recebe -s ou -es.'
_PARTIAL = 'Quase lá. Revise a forma do verbo que acompanha o sujeito.'
_INCORRECT = 'Revise a forma dos verbos no presente simples.'
_RUBRIC_LEVELS = (0, 25, 50, 75, 100)


@dataclass(frozen=True, slots=True)
class EnglishQuestionFormatsSeed:
    skill: Skill
    competency: Competency
    concept: Concept
    material: Material
    activities: tuple[Activity, ...]
    curriculum_sequence: CurriculumSequence


def _criterion(concept_id: str, *blank_keys: str) -> FillBlanksConceptCriterion:
    return FillBlanksConceptCriterion(
        concept_id=concept_id,
        criterion='Escolhe a forma verbal que concorda com o sujeito.',
        examples='She goes; they play.',
        limits='A grafia dos verbos não é observada.',
        blank_keys=blank_keys,
    )


def _fill_blanks_questions(concept_id: str) -> tuple[FillBlanksQuestion, ...]:
    prompt = 'Complete o texto com as palavras do banco.'
    return (
        FillBlanksQuestion(
            key='fill-1',
            prompt=prompt,
            content_language='en',
            segments=(
                FillBlanksSegment(text='My sister '),
                FillBlanksSegment(blank_key='b1'),
                FillBlanksSegment(text=' to school by bus and '),
                FillBlanksSegment(blank_key='b2'),
                FillBlanksSegment(text=' her homework every '),
                FillBlanksSegment(blank_key='b3'),
                FillBlanksSegment(text='.'),
            ),
            blanks=(
                FillBlanksBlank(key='b1', accepted_words=('goes', 'walks')),
                FillBlanksBlank(key='b2', accepted_words=('does',)),
                FillBlanksBlank(key='b3', accepted_words=('day',)),
            ),
            bank=(
                FillBlanksBankWord(key='w4', word='day'),
                FillBlanksBankWord(key='w6', word='go'),
                FillBlanksBankWord(key='w3', word='does'),
                FillBlanksBankWord(key='w1', word='goes'),
                FillBlanksBankWord(key='w5', word='day'),
                FillBlanksBankWord(key='w2', word='walks'),
            ),
            correct_explanation=_CORRECT,
            partial_explanation=_PARTIAL,
            incorrect_explanation=_INCORRECT,
            concept_criteria=(_criterion(concept_id, 'b1', 'b2'),),
        ),
        FillBlanksQuestion(
            key='fill-2',
            prompt=prompt,
            content_language='en',
            segments=(
                FillBlanksSegment(text='They '),
                FillBlanksSegment(blank_key='b1'),
                FillBlanksSegment(text=' football on Saturdays and '),
                FillBlanksSegment(blank_key='b2'),
                FillBlanksSegment(text=' TV on Sundays.'),
            ),
            blanks=(
                FillBlanksBlank(key='b1', accepted_words=('play',)),
                FillBlanksBlank(key='b2', accepted_words=('watch',)),
            ),
            bank=(
                FillBlanksBankWord(key='w3', word='plays'),
                FillBlanksBankWord(key='w2', word='watch'),
                FillBlanksBankWord(key='w4', word='watches'),
                FillBlanksBankWord(key='w1', word='play'),
            ),
            correct_explanation=_CORRECT,
            partial_explanation=_PARTIAL,
            incorrect_explanation=_INCORRECT,
            concept_criteria=(_criterion(concept_id, 'b1', 'b2'),),
        ),
        FillBlanksQuestion(
            key='fill-3',
            prompt=prompt,
            content_language='en',
            segments=(
                FillBlanksSegment(text='I '),
                FillBlanksSegment(blank_key='b1'),
                FillBlanksSegment(text=' English every morning.'),
            ),
            blanks=(FillBlanksBlank(key='b1', accepted_words=('study', 'practice')),),
            bank=(
                FillBlanksBankWord(key='w3', word='studies'),
                FillBlanksBankWord(key='w2', word='practice'),
                FillBlanksBankWord(key='w1', word='study'),
            ),
            correct_explanation=_CORRECT,
            incorrect_explanation=_INCORRECT,
            concept_criteria=(_criterion(concept_id, 'b1'),),
        ),
    )


def _choice_question(concept_id: str) -> SingleChoiceQuestion:
    return SingleChoiceQuestion(
        key='choice-1',
        prompt='Which sentence is correct?',
        options=(
            ChoiceOption(key='a', text='She go to work.', is_correct=False),
            ChoiceOption(key='b', text='She goes to work.', is_correct=True),
            ChoiceOption(key='c', text='She going to work.', is_correct=False),
        ),
        correct_explanation=_CORRECT,
        incorrect_explanation=_INCORRECT,
        concept_criteria=(
            ChoiceConceptCriterion(
                concept_id=concept_id,
                criterion='Reconhece a frase com o verbo concordando com o sujeito.',
                examples='She goes to work.',
                limits='Não observa a produção escrita.',
                correct_score=100,
                incorrect_score=0,
            ),
        ),
    )


def _translation_part(
    question_key: str, weight_percentage: int = 40
) -> TranslationRubricEvaluationPart:
    criteria = (
        ('semantic_preservation', 'Preservação do sentido', 70),
        ('grammatical_adequacy', 'Adequação gramatical', 30),
    )
    return TranslationRubricEvaluationPart(
        question_key=question_key,
        weight_percentage=weight_percentage,
        criteria=tuple(
            TranslationRubricCriterion(
                key=key,
                name=name,
                description=f'Avalia a {name.lower()} da tradução.',
                weight_percentage=weight,
                required=True,
                fixed_comments=tuple(
                    TranslationRubricComment(
                        id=f'en-{question_key}-{key}-{level}',
                        level=level,
                        text=(
                            f'{name}: a tradução está adequada.'
                            if level == 100
                            else f'{name}: a tradução ainda precisa de ajustes.'
                        ),
                    )
                    for level in _RUBRIC_LEVELS
                ),
                inconclusive_comment=TranslationInconclusiveComment(
                    id=f'en-{question_key}-{key}-inconclusive',
                    text='Não foi possível avaliar a resposta; tente novamente.',
                ),
            )
            for key, name, weight in criteria
        ),
    )


def _translation_question(
    key: str, concept_id: str, source_text: str, references: tuple[str, ...]
) -> TranslationQuestion:
    return TranslationQuestion(
        key=key,
        prompt='Traduza a frase para o inglês, digitando ou ditando a resposta.',
        source_language='pt-BR',
        target_language='en-US',
        source_text=source_text,
        reference_translations=references,
        concept_criteria=(
            CodeConceptCriterion(
                concept_id=concept_id,
                description='Usa o verbo no presente simples concordando com o sujeito.',
                level_observations=tuple(
                    CodeLevelObservation(
                        id=f'en-{key}-concept-{level}',
                        level=level,
                        evidence=f'A concordância verbal aparece no nível {level}.',
                        interpretation_limit='A tradução não mede vocabulário avançado.',
                    )
                    for level in _RUBRIC_LEVELS
                ),
                inconclusive_observation=CodeInconclusiveObservation(
                    id=f'en-{key}-concept-inconclusive',
                    text='Não há evidência suficiente para concluir.',
                ),
            ),
        ),
    )


def _translation_activity(competency_id: str, concept_id: str) -> Activity:
    return Activity.create(
        id=ENGLISH_TRANSLATION_ACTIVITY_ID,
        competency_id=competency_id,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.EASY,
        title='Presente simples: traduza as frases',
        objective='Traduzir frases curtas do português para o inglês.',
        questions=(
            _choice_question(concept_id),
            _translation_question(
                'translation-1',
                concept_id,
                'Minha irmã vai para a escola de ônibus.',
                (
                    'My sister goes to school by bus.',
                    'My sister takes the bus to school.',
                ),
            ),
            _translation_question(
                'translation-2',
                concept_id,
                'Eles jogam futebol aos sábados.',
                ('They play football on Saturdays.', 'They play soccer on Saturdays.'),
            ),
        ),
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(
                    question_key='choice-1', weight_percentage=20
                ),
                _translation_part('translation-1'),
                _translation_part('translation-2'),
            )
        ),
    )


def _opaque_pair_key(question_key: str, role: str, text: str) -> str:
    """Item keys come from the text, so they never reveal the pairing."""
    digest = sha256(f'{question_key}:{role}:{text}'.encode()).hexdigest()
    return f'{role}-{digest[:8]}'


def _pair_matching_question(
    key: str,
    concept_id: str,
    pairs: tuple[tuple[str, str], ...],
    display_order: tuple[int, ...],
) -> PairMatchingQuestion:
    words = tuple(
        PairMatchingItem(key=_opaque_pair_key(key, 'w', word), text=word)
        for word, _ in pairs
    )
    translations = tuple(
        PairMatchingItem(key=_opaque_pair_key(key, 't', translation), text=translation)
        for _, translation in pairs
    )
    return PairMatchingQuestion(
        key=key,
        prompt='Associe cada verbo em inglês à sua tradução.',
        source_language='en-US',
        target_language='pt-BR',
        words=words,
        translations=tuple(translations[index] for index in display_order),
        correct_pairs=tuple(
            PairMatchingPair(word_key=word.key, translation_key=translation.key)
            for word, translation in zip(words, translations, strict=True)
        ),
        full_explanation='Você associou corretamente todos os verbos.',
        partial_explanation='Você acertou parte das associações. Revise os verbos.',
        incorrect_explanation='Nenhuma associação está correta. Revise os verbos.',
        concept_criteria=(
            PairMatchingConceptCriterion(
                concept_id=concept_id,
                criterion='Reconhece o sentido de verbos comuns do presente simples.',
                examples='goes e vai',
                limits='A associação não mede produção escrita.',
                full_score=100,
                partial_score=50,
                incorrect_score=0,
            ),
        ),
    )


def _pair_matching_activity(competency_id: str, concept_id: str) -> Activity:
    return Activity.create(
        id=ENGLISH_PAIR_MATCHING_ACTIVITY_ID,
        competency_id=competency_id,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.MEDIUM,
        title='Presente simples: associe os verbos',
        objective='Associar verbos do presente simples às traduções em português.',
        questions=(
            _choice_question(concept_id),
            _pair_matching_question(
                'pairs-1',
                concept_id,
                (
                    ('goes', 'vai'),
                    ('plays', 'joga'),
                    ('watches', 'assiste'),
                    ('studies', 'estuda'),
                ),
                (2, 0, 3, 1),
            ),
            _pair_matching_question(
                'pairs-2',
                concept_id,
                (('works', 'trabalha'), ('reads', 'lê'), ('cooks', 'cozinha')),
                (1, 2, 0),
            ),
        ),
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(
                    question_key='choice-1', weight_percentage=20
                ),
                CorrectnessEvaluationPart(question_key='pairs-1', weight_percentage=40),
                CorrectnessEvaluationPart(question_key='pairs-2', weight_percentage=40),
            )
        ),
    )


def _fill_blanks_activity(competency_id: str, concept_id: str) -> Activity:
    return Activity.create(
        id=ENGLISH_FILL_BLANKS_ACTIVITY_ID,
        competency_id=competency_id,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.EASY,
        title='Presente simples: complete as frases',
        objective='Completar frases escolhendo o verbo que concorda com o sujeito.',
        questions=(*_fill_blanks_questions(concept_id), _choice_question(concept_id)),
        evaluation_rule=EvaluationRule(
            parts=tuple(
                CorrectnessEvaluationPart(question_key=key, weight_percentage=25)
                for key in ('fill-1', 'fill-2', 'fill-3', 'choice-1')
            )
        ),
    )


def _mixed_formats_activity(competency_id: str, concept_id: str) -> Activity:
    fill_blanks = _fill_blanks_questions(concept_id)[0]
    translation = _translation_question(
        'translation-1',
        concept_id,
        'Ele trabalha em um hospital.',
        ('He works at a hospital.', 'He works in a hospital.'),
    )
    questions = (
        fill_blanks,
        _pair_matching_question(
            'pairs-1',
            concept_id,
            (('goes', 'vai'), ('plays', 'joga'), ('watches', 'assiste')),
            (2, 0, 1),
        ),
        translation,
    )
    # One question per format; the weights must add up to 100.
    weights = (34, 33, 33)
    return Activity.create(
        id=ENGLISH_MIXED_FORMATS_ACTIVITY_ID,
        competency_id=competency_id,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.MEDIUM,
        title='Presente simples: complete, traduza e associe',
        objective=(
            'Completar frases, traduzir e associar verbos em uma mesma Atividade.'
        ),
        questions=questions,
        evaluation_rule=EvaluationRule(
            parts=tuple(
                _translation_part(question.key, weight_percentage=weight)
                if question is translation
                else CorrectnessEvaluationPart(
                    question_key=question.key, weight_percentage=weight
                )
                for question, weight in zip(questions, weights, strict=True)
            )
        ),
    )


def build_english_question_formats_seed() -> EnglishQuestionFormatsSeed:
    skill = Skill(
        id=ENGLISH_SKILL_ID,
        name='Inglês: presente simples',
        description='Verbos no presente simples em frases do dia a dia (exemplo).',
    )
    content = ReadySkillContentFaker.fake(
        skill=skill, id_for=lambda item: english_seed_id(100 + item)
    )
    competency_id = content.competency.id
    concept_id = content.concept.id
    replacements = {
        activity.id: activity
        for activity in (
            _fill_blanks_activity(competency_id, concept_id),
            _translation_activity(competency_id, concept_id),
            _pair_matching_activity(competency_id, concept_id),
            _mixed_formats_activity(competency_id, concept_id),
        )
    }
    placeholders = {activity.id: activity for activity in content.activities}
    for activity_id, activity in replacements.items():
        placeholder = placeholders.get(activity_id)
        if placeholder is None or placeholder.difficulty is not activity.difficulty:
            raise ValueError(
                'Each format must replace a placeholder of the same difficulty.'
            )

    return EnglishQuestionFormatsSeed(
        skill=skill,
        competency=content.competency,
        concept=content.concept,
        material=content.material,
        activities=tuple(
            replacements.get(activity.id, activity) for activity in content.activities
        ),
        curriculum_sequence=content.curriculum_sequence,
    )

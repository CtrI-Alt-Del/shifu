"""A fictional English Skill whose Learning Activity exercises fill-blanks questions.

The Skill reuses the placeholder content that makes any Skill startable and swaps its
first easy Learning Activity for one of word-bank questions. It is development
content for the example in SHIFU-123, not official Curriculum.
"""

from dataclasses import dataclass

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
    CorrectnessEvaluationPart,
    CurriculumSequence,
    EvaluationRule,
    FillBlanksBankWord,
    FillBlanksBlank,
    FillBlanksConceptCriterion,
    FillBlanksQuestion,
    FillBlanksSegment,
    SingleChoiceQuestion,
)
from shifu.fakers.curriculum.ready_skill_content_faker import ReadySkillContentFaker

ENGLISH_SEED_ID_PREFIX = '01SHFEN'


def english_seed_id(item: int) -> str:
    return f'{ENGLISH_SEED_ID_PREFIX}{item:019d}'


ENGLISH_SKILL_ID = english_seed_id(1)
# Content ids sit at 100 + the item number `ReadySkillContentFaker` assigns.
ENGLISH_COMPETENCY_ID = english_seed_id(101)
ENGLISH_FILL_BLANKS_ACTIVITY_ID = english_seed_id(110)

_CORRECT = 'Correto! Na terceira pessoa do singular, o verbo recebe -s ou -es.'
_PARTIAL = 'Quase lá. Revise a forma do verbo que acompanha o sujeito.'
_INCORRECT = 'Revise a forma dos verbos no presente simples.'


@dataclass(frozen=True, slots=True)
class EnglishFillBlanksSeed:
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
                FillBlanksBankWord(key='w1', word='goes'),
                FillBlanksBankWord(key='w2', word='walks'),
                FillBlanksBankWord(key='w3', word='does'),
                FillBlanksBankWord(key='w4', word='day'),
                FillBlanksBankWord(key='w5', word='day'),
                FillBlanksBankWord(key='w6', word='go'),
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
                FillBlanksBankWord(key='w1', word='play'),
                FillBlanksBankWord(key='w2', word='watch'),
                FillBlanksBankWord(key='w3', word='plays'),
                FillBlanksBankWord(key='w4', word='watches'),
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
                FillBlanksBankWord(key='w1', word='study'),
                FillBlanksBankWord(key='w2', word='practice'),
                FillBlanksBankWord(key='w3', word='studies'),
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


def build_english_fill_blanks_seed() -> EnglishFillBlanksSeed:
    skill = Skill(
        id=ENGLISH_SKILL_ID,
        name='Inglês: presente simples',
        description='Verbos no presente simples em frases do dia a dia (exemplo).',
    )
    content = ReadySkillContentFaker.fake(
        skill=skill, id_for=lambda item: english_seed_id(100 + item)
    )
    first_easy = content.activities[0]
    if first_easy.id != ENGLISH_FILL_BLANKS_ACTIVITY_ID:
        raise ValueError('The placeholder content must start with the easy Activity.')
    fill_blanks = _fill_blanks_questions(content.concept.id)
    activity = Activity.create(
        id=first_easy.id,
        competency_id=content.competency.id,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.EASY,
        title='Presente simples: complete as frases',
        objective='Completar frases escolhendo o verbo que concorda com o sujeito.',
        questions=(*fill_blanks, _choice_question(content.concept.id)),
        evaluation_rule=EvaluationRule(
            parts=tuple(
                CorrectnessEvaluationPart(question_key=key, weight_percentage=25)
                for key in ('fill-1', 'fill-2', 'fill-3', 'choice-1')
            )
        ),
    )
    return EnglishFillBlanksSeed(
        skill=skill,
        competency=content.competency,
        concept=content.concept,
        material=content.material,
        activities=(activity, *content.activities[1:]),
        curriculum_sequence=content.curriculum_sequence,
    )

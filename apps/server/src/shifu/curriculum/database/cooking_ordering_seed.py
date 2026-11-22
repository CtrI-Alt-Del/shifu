"""A fictional cooking Skill whose Learning Activity exercises step-ordering questions.

The Skill reuses the placeholder content that makes any Skill startable and swaps its
first easy Learning Activity for one of ordering questions. It is development content
for testing the format in SHIFU-129, not official Curriculum.
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
    CorrectnessEvaluationPart,
    CurriculumSequence,
    EvaluationRule,
    OrderingQuestion,
    OrderingStep,
)
from shifu.fakers.curriculum.ready_skill_content_faker import ReadySkillContentFaker

COOKING_SEED_ID_PREFIX = '01SHFCK'


def cooking_seed_id(item: int) -> str:
    return f'{COOKING_SEED_ID_PREFIX}{item:019d}'


COOKING_SKILL_ID = cooking_seed_id(1)
# Content ids sit at 100 + the item number `ReadySkillContentFaker` assigns.
COOKING_COMPETENCY_ID = cooking_seed_id(101)
COOKING_ORDERING_ACTIVITY_ID = cooking_seed_id(110)


@dataclass(frozen=True, slots=True)
class CookingOrderingSeed:
    skill: Skill
    competency: Competency
    concept: Concept
    material: Material
    activities: tuple[Activity, ...]
    curriculum_sequence: CurriculumSequence


def _ordering_question(
    key: str,
    concept_id: str,
    prompt: str,
    steps: tuple[tuple[str, str], ...],
    accepted_orders: tuple[tuple[str, ...], ...],
) -> OrderingQuestion:
    return OrderingQuestion(
        key=key,
        prompt=prompt,
        steps=tuple(OrderingStep(key=step_key, text=text) for step_key, text in steps),
        accepted_orders=accepted_orders,
        correct_explanation='A sequência respeita o que precisa acontecer antes de cada etapa.',
        incorrect_explanation='Confira o que precisa estar pronto antes de cada etapa.',
        concept_criteria=(
            ChoiceConceptCriterion(
                concept_id=concept_id,
                criterion='Organiza as etapas do preparo em uma sequência segura.',
                examples='Lavar antes de cortar; cortar antes de cozinhar.',
                limits='A ordenação não mede a execução prática.',
                correct_score=100,
                incorrect_score=0,
            ),
        ),
    )


def _ordering_activity(competency_id: str, concept_id: str) -> Activity:
    return Activity.create(
        id=COOKING_ORDERING_ACTIVITY_ID,
        competency_id=competency_id,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.EASY,
        title='Preparo de legumes: ordene as etapas',
        objective='Organizar as etapas de preparos simples na ordem correta.',
        questions=(
            _ordering_question(
                'ordering-1',
                concept_id,
                'Organize o preparo dos legumes.',
                (
                    ('wash', 'Lavar os legumes'),
                    ('peel', 'Descascar os legumes'),
                    ('cut', 'Cortar em cubos'),
                    ('boil', 'Cozinhar em água fervente'),
                    ('season', 'Temperar e servir'),
                ),
                (('wash', 'peel', 'cut', 'boil', 'season'),),
            ),
            # Two accepted orders: the pan can heat while the onion is chopped.
            _ordering_question(
                'ordering-2',
                concept_id,
                'Organize o preparo de uma cebola refogada.',
                (
                    ('chop', 'Picar a cebola'),
                    ('heat', 'Aquecer o azeite na panela'),
                    ('saute', 'Refogar a cebola até dourar'),
                ),
                (('chop', 'heat', 'saute'), ('heat', 'chop', 'saute')),
            ),
            _ordering_question(
                'ordering-3',
                concept_id,
                'Organize o preparo de uma salada.',
                (
                    ('wash', 'Lavar as folhas'),
                    ('dry', 'Secar as folhas'),
                    ('tear', 'Rasgar as folhas em pedaços'),
                    ('dress', 'Temperar na hora de servir'),
                ),
                (('wash', 'dry', 'tear', 'dress'),),
            ),
        ),
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(
                    question_key='ordering-1', weight_percentage=40
                ),
                CorrectnessEvaluationPart(
                    question_key='ordering-2', weight_percentage=30
                ),
                CorrectnessEvaluationPart(
                    question_key='ordering-3', weight_percentage=30
                ),
            )
        ),
    )


def build_cooking_ordering_seed() -> CookingOrderingSeed:
    skill = Skill(
        id=COOKING_SKILL_ID,
        name='Culinária: preparo de legumes',
        description='Etapas de preparos simples com legumes e verduras (exemplo).',
    )
    content = ReadySkillContentFaker.fake(
        skill=skill, id_for=lambda item: cooking_seed_id(100 + item)
    )
    first_easy = content.activities[0]
    if first_easy.id != COOKING_ORDERING_ACTIVITY_ID:
        raise ValueError('The placeholder content must start with the easy Activity.')

    activity = _ordering_activity(content.competency.id, content.concept.id)
    return CookingOrderingSeed(
        skill=skill,
        competency=content.competency,
        concept=content.concept,
        material=content.material,
        activities=(activity, *content.activities[1:]),
        curriculum_sequence=content.curriculum_sequence,
    )

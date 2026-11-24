"""A fictional cooking Skill whose Learning Activities exercise the newest question formats.

The Skill reuses the placeholder content that makes any Skill startable and swaps its
two easy Learning Activities: the first for step-ordering questions (SHIFU-129) and the
second for an Activity that mixes single choice with an image-choice question
(SHIFU-131). The first medium Activity mixes ordering, image-choice and practical
preparation (SHIFU-130) questions, for demonstration only. The support material is
written out so the Skill can be read end to end. It is development content for
testing the formats, not official Curriculum.
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
    ImageChoiceOption,
    ImageChoiceQuestion,
    OrderingQuestion,
    OrderingStep,
    SingleChoiceQuestion,
)
from shifu.fakers.curriculum.ready_skill_content_faker import ReadySkillContentFaker
from shifu.fakers.curriculum.structures import PracticalPreparationQuestionFaker

COOKING_SEED_ID_PREFIX = '01SHFCK'


def cooking_seed_id(item: int) -> str:
    return f'{COOKING_SEED_ID_PREFIX}{item:019d}'


COOKING_SKILL_ID = cooking_seed_id(1)
# Content ids sit at 100 + the item number `ReadySkillContentFaker` assigns.
COOKING_COMPETENCY_ID = cooking_seed_id(101)
COOKING_ORDERING_ACTIVITY_ID = cooking_seed_id(110)
COOKING_IMAGE_CHOICE_ACTIVITY_ID = cooking_seed_id(111)
COOKING_MIXED_FORMATS_ACTIVITY_ID = cooking_seed_id(112)

# Static files served by the web app from apps/web/public/curriculum/images/.
# Order: raw, translucent, caramelized, burnt.
COOKING_ONION_IMAGE_PATHS: tuple[str, str, str, str] = (
    '/curriculum/images/2d165276ed215938.webp',
    '/curriculum/images/51de9b1cc23dd653.webp',
    '/curriculum/images/5c8a6a6b47848a6f.webp',
    '/curriculum/images/655fecc77404ac40.webp',
)


@dataclass(frozen=True, slots=True)
class CookingQuestionFormatsSeed:
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


def _ordering_questions(
    concept_id: str,
) -> tuple[OrderingQuestion, OrderingQuestion, OrderingQuestion]:
    return (
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
    )


def _ordering_activity(competency_id: str, concept_id: str) -> Activity:
    return Activity.create(
        id=COOKING_ORDERING_ACTIVITY_ID,
        competency_id=competency_id,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.EASY,
        title='Preparo de legumes: ordene as etapas',
        objective='Organizar as etapas de preparos simples na ordem correta.',
        questions=_ordering_questions(concept_id),
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


def _cooking_criterion(
    concept_id: str, criterion: str, examples: str
) -> ChoiceConceptCriterion:
    return ChoiceConceptCriterion(
        concept_id=concept_id,
        criterion=criterion,
        examples=examples,
        limits='A questão não mede a execução prática do preparo.',
        correct_score=100,
        incorrect_score=0,
    )


def _single_choice_question(
    key: str,
    concept_id: str,
    prompt: str,
    options: tuple[tuple[str, str, bool], ...],
    correct_explanation: str,
    incorrect_explanation: str,
) -> SingleChoiceQuestion:
    return SingleChoiceQuestion(
        key=key,
        prompt=prompt,
        options=tuple(
            ChoiceOption(key=option_key, text=text, is_correct=is_correct)
            for option_key, text, is_correct in options
        ),
        correct_explanation=correct_explanation,
        incorrect_explanation=incorrect_explanation,
        concept_criteria=(
            _cooking_criterion(
                concept_id,
                'Relaciona o calor e o tempo ao ponto de cocção da cebola.',
                'Fogo baixo e tempo para adoçar; fogo alto queima antes de amaciar.',
            ),
        ),
    )


def _onion_image_choice_question(concept_id: str) -> ImageChoiceQuestion:
    raw, translucent, caramelized, burnt = COOKING_ONION_IMAGE_PATHS
    return ImageChoiceQuestion(
        key='image-choice-1',
        prompt='Qual destas cebolas está caramelizada?',
        options=(
            ImageChoiceOption(
                key='opt-7c1e94a05d32',
                image_path=raw,
                description='Fatias brancas e firmes, sem brilho, espalhadas na frigideira escura.',
                is_correct=False,
                feedback='Essa cebola ainda está crua.',
            ),
            ImageChoiceOption(
                key='opt-b82f6d1e4a97',
                image_path=translucent,
                description='Fatias macias e quase transparentes, com brilho úmido e sem cor.',
                is_correct=False,
                feedback='Essa cebola já amoleceu, mas ainda não ganhou cor.',
            ),
            ImageChoiceOption(
                key='opt-1d5a0e83f6c4',
                image_path=caramelized,
                description='Fios macios de cor de mel escuro, com brilho de calda, soltos na frigideira.',
                is_correct=True,
                feedback='Essa cebola chegou ao ponto: macia, escura e com brilho de calda.',
            ),
            ImageChoiceOption(
                key='opt-e9370b2c58d1',
                image_path=burnt,
                description='Pedaços encolhidos e secos, de cor quase preta, com as bordas duras.',
                is_correct=False,
                feedback='Essa cebola passou do ponto e queimou.',
            ),
        ),
        correct_explanation='A cebola caramelizada fica macia e escura porque o açúcar natural dourou aos poucos, sem queimar.',
        incorrect_explanation='A caramelização acontece em etapas, com o açúcar da cebola escurecendo aos poucos. Observe a cor e a textura de cada imagem e tente de novo em outra passagem.',
        concept_criteria=(
            _cooking_criterion(
                concept_id,
                'Reconhece o ponto de caramelização pela cor e pela textura.',
                'Cebola macia, escura e brilhante, sem partes queimadas.',
            ),
        ),
    )


def _image_choice_activity(competency_id: str, concept_id: str) -> Activity:
    return Activity.create(
        id=COOKING_IMAGE_CHOICE_ACTIVITY_ID,
        competency_id=competency_id,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.EASY,
        title='Ponto de cocção',
        objective='Reconhecer o ponto de cocção de uma cebola pela aparência.',
        questions=(
            _single_choice_question(
                'single-choice-1',
                concept_id,
                'Em fogo médio-baixo, por que a cebola leva tempo para caramelizar?',
                (
                    (
                        'time',
                        'Porque o açúcar natural da cebola escurece aos poucos, com calor suave.',
                        True,
                    ),
                    (
                        'water',
                        'Porque a cebola precisa ferver em água antes de dourar.',
                        False,
                    ),
                    (
                        'salt',
                        'Porque o sal só começa a agir depois de vinte minutos.',
                        False,
                    ),
                ),
                'Calor suave dá tempo para o açúcar da cebola escurecer sem queimar.',
                'Pense no que muda na cebola enquanto ela cozinha em calor suave.',
            ),
            _onion_image_choice_question(concept_id),
            _single_choice_question(
                'single-choice-2',
                concept_id,
                'O que acontece com a cebola quando o fogo está muito alto?',
                (
                    (
                        'burn',
                        'Ela queima por fora antes de amaciar e adoçar por dentro.',
                        True,
                    ),
                    (
                        'sweet',
                        'Ela fica mais doce e macia em poucos minutos.',
                        False,
                    ),
                    (
                        'same',
                        'Ela solta o líquido e continua com a mesma cor.',
                        False,
                    ),
                ),
                'Fogo alto escurece a superfície depressa, e o interior não tem tempo de amaciar.',
                'Compare o que o calor forte faz com a superfície e com o interior da cebola.',
            ),
        ),
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(
                    question_key='single-choice-1', weight_percentage=30
                ),
                CorrectnessEvaluationPart(
                    question_key='image-choice-1', weight_percentage=40
                ),
                CorrectnessEvaluationPart(
                    question_key='single-choice-2', weight_percentage=30
                ),
            )
        ),
    )


def _mixed_formats_activity(competency_id: str, concept_id: str) -> Activity:
    _, onion, _ = _ordering_questions(concept_id)
    practical = PracticalPreparationQuestionFaker.fake(
        key='practical-1',
        concept_criteria=(
            PracticalPreparationQuestionFaker.concept_criterion(concept_id),
        ),
    )
    questions = (onion, _onion_image_choice_question(concept_id), practical)
    weights = (30, 30, 40)
    return Activity.create(
        id=COOKING_MIXED_FORMATS_ACTIVITY_ID,
        competency_id=competency_id,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.MEDIUM,
        title='Cebola e legumes: ordene, reconheça e prepare',
        objective=(
            'Ordenar etapas, reconhecer o ponto da cebola e preparar legumes salteados.'
        ),
        questions=questions,
        evaluation_rule=EvaluationRule(
            parts=tuple(
                CorrectnessEvaluationPart(
                    question_key=question.key, weight_percentage=weight
                )
                for question, weight in zip(questions, weights, strict=True)
            )
        ),
    )


_MATERIAL_CONTENT = """\
Preparar legumes bem começa antes do fogo. Este material mostra como lavar,
cortar, refogar e saltear legumes, e como reconhecer o ponto certo de cada
preparo.

Organize tudo antes de começar. Na cozinha, a ordem das etapas evita erros e
acidentes. Antes de acender o fogo, deixe os legumes lavados, descascados e
cortados, os temperos separados e os utensílios à mão. Assim você não precisa
cortar nada com a panela já quente.

A sequência básica de qualquer preparo com legumes é lavar, descascar, cortar,
cozinhar e, por fim, temperar e servir. Lave sempre antes de descascar e
cortar: se você cortar primeiro, a sujeira da casca passa para a parte de
dentro do legume.

Folhas pedem um cuidado extra. Lave, seque bem e rasgue em pedaços. Só tempere
na hora de servir, porque o sal e o vinagre murcham as folhas em poucos
minutos.

Faça cortes regulares. Pedaços do mesmo tamanho cozinham no mesmo tempo. Se
uns forem grandes e outros pequenos, os pequenos queimam enquanto os grandes
ainda estão crus.

Os cortes mais usados são as rodelas, boas para cenoura e abobrinha; a
meia-lua, que é a rodela cortada ao meio; as tiras, finas e compridas como no
pimentão; os cubos, com os lados iguais; e o picado, em pedaços bem pequenos,
usado na cebola e no alho.

Para cortar com segurança, apoie o legume numa tábua firme, dobre a ponta dos
dedos da mão que segura e use uma faca bem afiada. Uma faca cega escorrega e
machuca mais.

Refogar é cozinhar em pouca gordura, mexendo de vez em quando, até o alimento
amaciar e ganhar sabor. Para refogar uma cebola, primeiro pique a cebola,
depois aqueça o azeite na panela e só então coloque a cebola, mexendo até ela
ficar transparente ou dourada.

Com o calor, a cebola muda de aspecto em etapas. Crua, ela é branca, firme e
sem brilho. Transparente, fica macia, quase translúcida e brilhante, ótima como
base de arroz, molhos e sopas. Dourada, ganha bordas douradas e um sabor mais
doce. Caramelizada, fica macia, com cor de mel escuro e brilho de calda.
Queimada, fica quase preta, seca e amarga, e deve ser descartada.

A caramelização acontece quando o açúcar natural da cebola doura devagar. Ela
pede fogo baixo e paciência, de 30 a 40 minutos, mexendo de tempos em tempos.
Com fogo alto, a cebola queima por fora antes de amaciar por dentro.

Saltear é cozinhar rápido em fogo alto, com pouca gordura, mexendo sempre. Os
legumes ficam dourados por fora e ainda firmes por dentro.

Para um bom salteado, aqueça bem a frigideira antes de colocar os legumes. Não
coloque legumes demais de uma vez: amontoados, eles soltam água e cozinham no
vapor, sem dourar. Se precisar, salteie em partes. Comece pelos legumes mais
firmes, porque a cenoura demora mais que a abobrinha e o pimentão. Mexa com
frequência para dourar por igual e tempere só no final, já que o sal no início
faz os legumes soltarem água.

O ponto certo do salteado é quando os legumes estão brilhantes, com as bordas
douradas e ainda um pouco crocantes ao morder.

Por fim, capriche na apresentação. Sirva em um prato limpo, organize os
legumes no centro, sem espalhar pela borda, e finalize com ervas frescas, como
salsinha. Limpe os respingos da borda com um pano antes de servir.

Para lembrar: organize tudo antes de acender o fogo, corte os legumes do mesmo
tamanho, use fogo baixo para caramelizar a cebola e fogo alto para saltear,
não encha demais a frigideira e tempere no final.
"""


def build_cooking_question_formats_seed() -> CookingQuestionFormatsSeed:
    skill = Skill(
        id=COOKING_SKILL_ID,
        name='Culinária: preparo de legumes',
        description='Etapas de preparos simples com legumes e verduras (exemplo).',
    )
    content = ReadySkillContentFaker.fake(
        skill=skill, id_for=lambda item: cooking_seed_id(100 + item)
    )
    first_easy, second_easy, first_medium = content.activities[:3]
    if (
        first_easy.id != COOKING_ORDERING_ACTIVITY_ID
        or second_easy.id != COOKING_IMAGE_CHOICE_ACTIVITY_ID
        or first_medium.id != COOKING_MIXED_FORMATS_ACTIVITY_ID
        or first_medium.difficulty is not ActivityDifficulty.MEDIUM
    ):
        raise ValueError(
            'The placeholder content must start with two easy and one medium Activity.'
        )

    return CookingQuestionFormatsSeed(
        skill=skill,
        competency=content.competency,
        concept=content.concept,
        material=Material(
            id=content.material.id,
            skill_id=content.material.skill_id,
            title=content.material.title,
            content=_MATERIAL_CONTENT,
            material_type=content.material.material_type,
            concept_ids=content.material.concept_ids,
        ),
        activities=(
            _ordering_activity(content.competency.id, content.concept.id),
            _image_choice_activity(content.competency.id, content.concept.id),
            _mixed_formats_activity(content.competency.id, content.concept.id),
            *content.activities[3:],
        ),
        curriculum_sequence=content.curriculum_sequence,
    )

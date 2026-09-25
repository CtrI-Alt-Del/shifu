from datetime import UTC, datetime
from decimal import Decimal

from shifu.communication.core.domain.entities import Communication, DeliveryAttempt
from shifu.communication.core.domain.enums import (
    CommunicationChannel,
    CommunicationStatus,
    CommunicationType,
    DeliveryAttemptStatus,
)
from shifu.communication.core.domain.structures import MessageContent
from shifu.curriculum.core.domain.entities import (
    Activity,
    Competency,
    Concept,
    Material,
    Skill,
)
from shifu.fakers.curriculum.entities import (
    ActivityFaker,
    CompetencyFaker,
    MaterialFaker,
    SkillFaker,
)
from shifu.curriculum.core.domain.structures import (
    ActivitySequenceItem,
    ActivityQuestion,
    ChoiceConceptCriterion,
    ChoiceOption,
    CorrectnessEvaluationPart,
    CurriculumSequence,
    EvaluationRule,
    MaterialSequenceItem,
    MultipleSelectionQuestion,
    SingleChoiceQuestion,
    SkillFoundation,
)
from shifu.curriculum.core.domain.enums import (
    ActivityDifficulty,
    ActivityType,
    MaterialType,
)
from shifu.identity.core.domain.entities import Account, AccountActionToken
from shifu.fakers.identity.entities import AccountFaker
from shifu.identity.providers.auth.password_hashing.argon2id_hash_provider import (
    Argon2idHashProvider,
)
from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    CompetencyProgress,
    Goal,
    SkillExperience,
)
from shifu.learning.core.domain.adaptive_learning_policy import AdaptiveLearningPolicy
from shifu.fakers.learning.entities import (
    ActivityAttemptFaker,
    ActivityEvaluationFaker,
    CompetencyProgressFaker,
    GoalFaker,
    SkillExperienceFaker,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.shared.core.domain.structures import structure


SEED_ACCOUNT_ID = '01SHF000000000000000000001'
SEED_SKILL_LOGIC_ID = '01SHF000000000000000000002'
SEED_SKILL_PYTHON_ID = '01SHF000000000000000000003'
SEED_COMPETENCY_VARIABLES_ID = '01SHF000000000000000000004'
SEED_COMPETENCY_CONDITIONS_ID = '01SHF000000000000000000005'
SEED_COMPETENCY_FUNCTIONS_ID = '01SHF000000000000000000006'
SEED_COMPETENCY_REPETITION_ID = '01SHF000000000000000000020'
SEED_MATERIAL_LOGIC_ID = '01SHF000000000000000000007'
SEED_MATERIAL_PYTHON_ID = '01SHF000000000000000000008'
SEED_MATERIAL_REPETITION_INTRO_ID = '01SHF000000000000000000021'
SEED_MATERIAL_REPETITION_FOR_ID = '01SHF000000000000000000022'
SEED_ACTIVITY_VARIABLES_ID = '01SHF000000000000000000009'
SEED_ACTIVITY_CONDITIONS_ID = '01SHF000000000000000000010'
SEED_ACTIVITY_FUNCTIONS_ID = '01SHF000000000000000000011'
SEED_ACTIVITY_REPETITION_EASY_ID = '01SHF000000000000000000023'
SEED_ACTIVITY_REPETITION_MEDIUM_ID = '01SHF000000000000000000024'
SEED_ACTIVITY_REPETITION_HARD_ID = '01SHF000000000000000000025'
SEED_GOAL_ID = '01SHF000000000000000000012'
SEED_LOGIC_EXPERIENCE_ID = '01SHF000000000000000000013'
SEED_PYTHON_EXPERIENCE_ID = '01SHF000000000000000000014'
SEED_PROGRESS_ID = '01SHF000000000000000000015'
SEED_ATTEMPT_ID = '01SHF000000000000000000016'
SEED_EVALUATION_ID = '01SHF000000000000000000017'
SEED_COMMUNICATION_ID = '01SHF000000000000000000018'
SEED_DELIVERY_ATTEMPT_ID = '01SHF000000000000000000019'
SEED_REPETITION_PROGRESS_ID = '01SHF000000000000000000026'
SEED_REPETITION_ATTEMPT_ID = '01SHF000000000000000000027'
SEED_REPETITION_EVALUATION_ID = '01SHF000000000000000000028'
SEED_CONDITIONS_PROGRESS_ID = '01SHF000000000000000000029'
SEED_CONDITIONS_ATTEMPT_ID = '01SHF000000000000000000030'
SEED_CONDITIONS_EVALUATION_ID = '01SHF000000000000000000031'
SEED_ADAPTIVE_SKILL_ID = '01SHF000000000000000000032'
SEED_ADAPTIVE_COMPETENCY_ID = '01SHF000000000000000000033'
SEED_ADAPTIVE_CONCEPT_ID = '01SHF000000000000000000034'
SEED_ADAPTIVE_MATERIAL_ID = '01SHF000000000000000000035'
SEED_ADAPTIVE_ACTIVITY_IDS = tuple(
    f'01SHF000000000000000000{number:03d}' for number in range(36, 45)
)
SEED_ADAPTIVE_LAB_SKILL_ID = '01SHF000000000000000000045'
SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID = '01SHF000000000000000000046'
SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID = '01SHF000000000000000000047'
SEED_ADAPTIVE_LAB_CONDITIONS_CONCEPT_ID = '01SHF000000000000000000048'
SEED_ADAPTIVE_LAB_PRIORITY_CONCEPT_ID = '01SHF000000000000000000049'
SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID = '01SHF000000000000000000050'
SEED_ADAPTIVE_LAB_PRIORITY_MATERIAL_ID = '01SHF000000000000000000051'
SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS = tuple(
    f'01SHF000000000000000000{number:03d}' for number in range(52, 61)
)
SEED_ADAPTIVE_LAB_PRIORITY_ACTIVITY_IDS = tuple(
    f'01SHF000000000000000000{number:03d}' for number in range(61, 70)
)
SEED_ADAPTIVE_LAB_GOAL_ID = '01SHF000000000000000000070'
SEED_ADAPTIVE_LAB_EXPERIENCE_ID = '01SHF000000000000000000071'
SEED_ADAPTIVE_LAB_CONDITIONS_PROGRESS_ID = '01SHF000000000000000000072'
SEED_ADAPTIVE_LAB_PRIORITY_PROGRESS_ID = '01SHF000000000000000000073'
SEED_ADAPTIVE_LAB_BOOLEAN_CONCEPT_ID = '01SHF000000000000000000074'
SEED_ADAPTIVE_LAB_BOOLEAN_MATERIAL_ID = '01SHF000000000000000000075'
SEED_ADAPTIVE_LAB_BOOLEAN_ACTIVITY_IDS = tuple(
    f'01SHF000000000000000000{number:03d}' for number in range(76, 85)
)
SEED_GRAPH_GOAL_ID = '01SHF000000000000000000200'
SEED_GRAPH_DATA_STRUCTURES_SKILL_ID = '01SHF000000000000000000201'
SEED_GRAPH_SEARCH_SKILL_ID = '01SHF000000000000000000202'
SEED_GRAPH_DATA_MODELING_SKILL_ID = '01SHF000000000000000000203'
SEED_GRAPH_APIS_SKILL_ID = '01SHF000000000000000000204'
SEED_GRAPH_TESTING_SKILL_ID = '01SHF000000000000000000205'
SEED_GRAPH_PROJECT_SKILL_ID = '01SHF000000000000000000206'
SEED_GRAPH_SKILL_IDS = (
    SEED_SKILL_LOGIC_ID,
    SEED_SKILL_PYTHON_ID,
    SEED_ADAPTIVE_SKILL_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
    SEED_GRAPH_DATA_STRUCTURES_SKILL_ID,
    SEED_GRAPH_SEARCH_SKILL_ID,
    SEED_GRAPH_DATA_MODELING_SKILL_ID,
    SEED_GRAPH_APIS_SKILL_ID,
    SEED_GRAPH_TESTING_SKILL_ID,
    SEED_GRAPH_PROJECT_SKILL_ID,
)
SEED_GRAPH_EXPERIENCE_IDS = tuple(
    f'01SHF000000000000000000{number:03d}' for number in range(210, 220)
)

SEED_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
SEED_ACCOUNT_PASSWORD: str = 'ShifuSeed123!'


@structure
class DevelopmentSeed:
    accounts: tuple[Account, ...]
    account_action_tokens: tuple[AccountActionToken, ...]
    skills: tuple[Skill, ...]
    skill_foundations: tuple[SkillFoundation, ...]
    competencies: tuple[Competency, ...]
    concepts: tuple[Concept, ...]
    materials: tuple[Material, ...]
    activities: tuple[Activity, ...]
    curriculum_sequences: tuple[CurriculumSequence, ...]
    goals: tuple[Goal, ...]
    skill_experiences: tuple[SkillExperience, ...]
    competency_progresses: tuple[CompetencyProgress, ...]
    activity_attempts: tuple[ActivityAttempt, ...]
    activity_evaluations: tuple[ActivityEvaluation, ...]
    communications: tuple[Communication, ...]
    delivery_attempts: tuple[DeliveryAttempt, ...]


@structure
class _MultipleSelectionSeedQuestion:
    prompt: str
    options: tuple[tuple[str, str, bool], ...]


def _adaptive_choice_activity(
    *,
    activity_id: str,
    competency_id: str,
    concept_id: str,
    activity_type: ActivityType,
    difficulty: ActivityDifficulty,
    title: str,
    objective: str,
    items: tuple[tuple[str, str, str, str] | _MultipleSelectionSeedQuestion, ...],
    required_concept_ids: tuple[str, ...] = (),
) -> Activity:
    questions: list[ActivityQuestion] = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, _MultipleSelectionSeedQuestion):
            options = tuple(
                ChoiceOption(key=key, text=label, is_correct=is_correct)
                for key, label, is_correct in item.options
            )
            questions.append(
                MultipleSelectionQuestion(
                    key=f'q{index}',
                    prompt=item.prompt,
                    options=options,
                    correct_explanation='Todas e somente as afirmações verdadeiras foram selecionadas.',
                    incorrect_explanation='Reavalie cada afirmação; a seleção deve ser completa e exata.',
                    concept_criteria=(
                        ChoiceConceptCriterion(
                            concept_id=concept_id,
                            criterion='Identifica todas as condições verdadeiras sem incluir as falsas.',
                            examples=', '.join(
                                option.text for option in options if option.is_correct
                            ),
                            limits='A seleção não mede implementação de código.',
                            correct_score=100,
                            incorrect_score=0,
                        ),
                    ),
                )
            )
            continue

        prompt, option_a, option_b, correct_key = item
        questions.append(
            SingleChoiceQuestion(
                key=f'q{index}',
                prompt=prompt,
                options=(
                    ChoiceOption(key='a', text=option_a, is_correct=correct_key == 'a'),
                    ChoiceOption(key='b', text=option_b, is_correct=correct_key == 'b'),
                ),
                correct_explanation='A alternativa segue a condição definida no enunciado.',
                incorrect_explanation='Revise a condição e o ramo executado.',
                concept_criteria=(
                    ChoiceConceptCriterion(
                        concept_id=concept_id,
                        criterion='Identifica o ramo executado a partir da condição explícita.',
                        examples=option_a if correct_key == 'a' else option_b,
                        limits='Esta resposta não mede implementação de código.',
                        correct_score=100,
                        incorrect_score=0,
                    ),
                ),
            )
        )
    base_weight, extra_weights = divmod(100, len(questions))
    weights = tuple(
        base_weight + (1 if index < extra_weights else 0)
        for index in range(len(questions))
    )
    return Activity(
        id=activity_id,
        competency_id=competency_id,
        activity_type=activity_type,
        difficulty=difficulty,
        title=title,
        objective=objective,
        required_concept_ids=required_concept_ids,
        questions=tuple(questions),
        evaluation_rule=EvaluationRule(
            parts=tuple(
                CorrectnessEvaluationPart(
                    question_key=question.key, weight_percentage=weight
                )
                for question, weight in zip(questions, weights, strict=True)
            )
        ),
    )


def _adaptive_activities() -> tuple[Activity, ...]:
    scenarios = (
        (
            ActivityType.DIAGNOSTIC,
            ActivityDifficulty.EASY,
            'Diagnóstico: decisão direta',
            'Identificar um ramo simples.',
            (
                (
                    'Se idade 17 é menor que 18, qual saída?',
                    'Menor de idade',
                    'Maior de idade',
                    'a',
                ),
            ),
        ),
        (
            ActivityType.DIAGNOSTIC,
            ActivityDifficulty.MEDIUM,
            'Diagnóstico: condições conjuntas',
            'Aplicar duas condições.',
            (
                (
                    'A entrada exige ingresso e documento; há ingresso, mas não documento. Entra?',
                    'Sim',
                    'Não',
                    'b',
                ),
            ),
        ),
        (
            ActivityType.DIAGNOSTIC,
            ActivityDifficulty.HARD,
            'Diagnóstico: precedência de regras',
            'Resolver regras com prioridade.',
            (
                (
                    'Urgência tem prioridade sobre ordem de chegada; a pessoa chegou depois e é urgente. Quem vai primeiro?',
                    'A pessoa urgente',
                    'Quem chegou antes',
                    'a',
                ),
            ),
        ),
        (
            ActivityType.LEARNING,
            ActivityDifficulty.EASY,
            'Decisões na fila',
            'Escolher ramos em uma fila de atendimento.',
            (
                ('Se a fila está vazia, o atendente chama alguém?', 'Não', 'Sim', 'a'),
                (
                    'Se há senha preferencial, qual fila é chamada primeiro?',
                    'Preferencial',
                    'Comum',
                    'a',
                ),
                (
                    'Sem senha preferencial, qual fila é chamada?',
                    'Comum',
                    'Nenhuma',
                    'a',
                ),
            ),
        ),
        (
            ActivityType.LEARNING,
            ActivityDifficulty.EASY,
            'Entrada no cinema',
            'Aplicar condições de entrada.',
            (
                (
                    'A sessão exige ingresso; Ana não tem ingresso. Ela entra?',
                    'Sim',
                    'Não',
                    'b',
                ),
                (
                    'A classificação é 16; Beto tem 18. A idade permite entrada?',
                    'Permite',
                    'Impede',
                    'a',
                ),
                (
                    'A classificação é 18; Cris tem 17. A idade permite entrada?',
                    'Permite',
                    'Impede',
                    'b',
                ),
            ),
        ),
        (
            ActivityType.LEARNING,
            ActivityDifficulty.MEDIUM,
            'Faixas de frete',
            'Interpretar condições por faixas de valor.',
            (
                (
                    'Frete grátis vale para pedido de R$ 100 ou mais; pedido de R$ 99 recebe?',
                    'Sim',
                    'Não',
                    'b',
                ),
                ('Pedido de R$ 100 recebe frete grátis?', 'Sim', 'Não', 'a'),
                (
                    'Cupom exige frete pago; pedido com frete grátis usa o cupom?',
                    'Sim',
                    'Não',
                    'b',
                ),
            ),
        ),
        (
            ActivityType.LEARNING,
            ActivityDifficulty.MEDIUM,
            'Credenciais de evento',
            'Combinar condições de acesso.',
            (
                (
                    'Acesso exige convite e documento; Rui tem ambos. Entra?',
                    'Entra',
                    'Não entra',
                    'a',
                ),
                (
                    'Lia tem convite, mas não documento. Entra?',
                    'Entra',
                    'Não entra',
                    'b',
                ),
                (
                    'Noa tem documento, mas não convite. Entra?',
                    'Entra',
                    'Não entra',
                    'b',
                ),
            ),
        ),
        (
            ActivityType.LEARNING,
            ActivityDifficulty.HARD,
            'Triagem de suporte',
            'Aplicar prioridade e exceções.',
            (
                (
                    'Incidente crítico tem prioridade sobre horário; chegou por último. Vai primeiro?',
                    'Sim',
                    'Não',
                    'a',
                ),
                (
                    'Sem incidentes críticos, a regra é ordem de chegada. A última pessoa vai primeiro?',
                    'Sim',
                    'Não',
                    'b',
                ),
                (
                    'Um chamado crítico foi resolvido; outro comum chegou antes de um novo crítico. Qual segue?',
                    'Novo crítico',
                    'Comum antigo',
                    'a',
                ),
            ),
        ),
        (
            ActivityType.LEARNING,
            ActivityDifficulty.HARD,
            'Promoções combinadas',
            'Aplicar precedência entre regras comerciais.',
            (
                (
                    'Regra: cupom VIP substitui desconto comum. Cliente VIP tem ambos; qual vale?',
                    'VIP',
                    'Comum',
                    'a',
                ),
                (
                    'Sem cupom VIP, o desconto comum de 10% está ativo. Qual vale?',
                    'Nenhum',
                    'Comum',
                    'b',
                ),
                (
                    'Regra: produto em liquidação não aceita cupons. Há cupom VIP e liquidação; qual vale?',
                    'Liquidação',
                    'VIP',
                    'a',
                ),
            ),
        ),
    )
    return tuple(
        _adaptive_choice_activity(
            activity_id=activity_id,
            competency_id=SEED_ADAPTIVE_COMPETENCY_ID,
            concept_id=SEED_ADAPTIVE_CONCEPT_ID,
            activity_type=activity_type,
            difficulty=difficulty,
            title=title,
            objective=objective,
            items=items,
        )
        for activity_id, (activity_type, difficulty, title, objective, items) in zip(
            SEED_ADAPTIVE_ACTIVITY_IDS, scenarios, strict=True
        )
    )


def _adaptive_lab_activities() -> tuple[Activity, ...]:
    # Three diagnostic levels plus two independent learning Activities per level
    # let a learner observe coverage, replacement, mastery and regression.
    conditions = (
        (
            'Diagnóstico: comparar valores',
            'Reconhecer uma condição simples',
            (
                (
                    'Considere o código:\n\n```python\nidade = 17\nlimite = 18\npode_entrar = idade >= limite\n```\n\nQual é o valor de `pode_entrar`?',
                    'True',
                    'False',
                    'b',
                ),
            ),
        ),
        (
            'Diagnóstico: incluir o limite',
            'Verificar um limite inclusivo',
            (('100 é maior ou igual a 100?', 'Sim', 'Não', 'a'),),
        ),
        (
            'Diagnóstico: combinar condições',
            'Avaliar uma conjunção',
            (
                (
                    'Acesso exige crachá e código; há só crachá. Libera?',
                    'Sim',
                    'Não',
                    'b',
                ),
            ),
        ),
        (
            'Entrada por idade',
            'Aplicar comparações simples',
            (
                ('18 é maior que 16?', 'Sim', 'Não', 'a'),
                ('15 é maior que 16?', 'Sim', 'Não', 'b'),
                ('16 é igual a 16?', 'Sim', 'Não', 'a'),
                _MultipleSelectionSeedQuestion(
                    prompt=(
                        'Considere o código:\n\n```python\n'
                        'idade = 16\nidade_minima = 16\n'
                        'pode_entrar = idade >= idade_minima\n'
                        '```\n\nQuais afirmações são verdadeiras?'
                    ),
                    options=(
                        ('a', 'idade == idade_minima é True.', True),
                        ('b', 'pode_entrar é True.', True),
                        ('c', 'idade > idade_minima é True.', False),
                        ('d', 'idade < idade_minima é True.', False),
                    ),
                ),
                _MultipleSelectionSeedQuestion(
                    prompt=(
                        'Considere o código:\n\n```python\n'
                        'idade = 17\nlimite = 18\n'
                        'menor_de_idade = idade < limite\n'
                        '```\n\nQuais afirmações são verdadeiras?'
                    ),
                    options=(
                        ('a', 'menor_de_idade é True.', True),
                        ('b', 'idade <= limite é True.', True),
                        ('c', 'idade == limite é True.', False),
                        ('d', 'idade > limite é True.', False),
                    ),
                ),
            ),
        ),
        (
            'Fila com limite',
            'Testar condições de lotação',
            (
                ('A fila aceita até 5; há 4. Cabe mais uma?', 'Sim', 'Não', 'a'),
                ('A fila aceita até 5; há 5. Cabe mais uma?', 'Sim', 'Não', 'b'),
                ('A fila aceita até 5; há 6. Está acima do limite?', 'Sim', 'Não', 'a'),
            ),
        ),
        (
            'Faixa de desconto',
            'Avaliar limites inclusivos',
            (
                (
                    'Desconto começa em R$ 50; compra de R$ 49 recebe?',
                    'Sim',
                    'Não',
                    'b',
                ),
                ('Compra de R$ 50 recebe desconto?', 'Sim', 'Não', 'a'),
                ('Compra de R$ 51 recebe desconto?', 'Sim', 'Não', 'a'),
            ),
        ),
        (
            'Acesso com duas condições',
            'Aplicar uma conjunção',
            (
                (
                    'Acesso exige ingresso e documento; há os dois. Entra?',
                    'Sim',
                    'Não',
                    'a',
                ),
                ('Há ingresso, mas falta documento. Entra?', 'Sim', 'Não', 'b'),
                ('Há documento, mas falta ingresso. Entra?', 'Sim', 'Não', 'b'),
            ),
        ),
        (
            'Condições com negação',
            'Combinar requisitos e bloqueios',
            (
                (
                    'Libera se tem senha e não está bloqueado; tem senha e bloqueio. Libera?',
                    'Sim',
                    'Não',
                    'b',
                ),
                ('Tem senha e não está bloqueado. Libera?', 'Sim', 'Não', 'a'),
                ('Não tem senha e não está bloqueado. Libera?', 'Sim', 'Não', 'b'),
            ),
        ),
        (
            'Limites combinados',
            'Resolver intervalos e exceções',
            (
                (
                    'Faixa aceita de 10 a 20, inclusive; valor 10 entra?',
                    'Sim',
                    'Não',
                    'a',
                ),
                ('Valor 21 entra na faixa?', 'Sim', 'Não', 'b'),
                ('Valor 20 entra na faixa?', 'Sim', 'Não', 'a'),
            ),
        ),
    )
    boolean = (
        (
            'Diagnóstico: regra E',
            'Exigir duas condições verdadeiras',
            (
                _MultipleSelectionSeedQuestion(
                    prompt='A entrada exige senha **e** documento. Quais pessoas podem entrar?',
                    options=(
                        ('a', 'Ana tem senha e documento.', True),
                        ('b', 'Beto tem apenas senha.', False),
                        ('c', 'Cris tem documento e senha.', True),
                        ('d', 'Dani tem apenas documento.', False),
                    ),
                ),
            ),
        ),
        (
            'Diagnóstico: regra OU',
            'Aceitar uma alternativa válida',
            (('Basta ingresso ou convite; há convite. Entra?', 'Sim', 'Não', 'a'),),
        ),
        (
            'Diagnóstico: negação',
            'Combinar uma condição com impedimento',
            (
                (
                    'Libera com senha e sem bloqueio; há senha e bloqueio. Libera?',
                    'Sim',
                    'Não',
                    'b',
                ),
            ),
        ),
        (
            'Duas exigências',
            'Praticar conjunção',
            (
                _MultipleSelectionSeedQuestion(
                    prompt=(
                        'Considere o código:\n\n```python\n'
                        'tem_cracha = True\ntem_senha = False\n'
                        'pode_entrar = tem_cracha and tem_senha\n'
                        '```\n\nQuais afirmações são verdadeiras?'
                    ),
                    options=(
                        ('a', 'tem_cracha é True.', True),
                        ('b', 'tem_senha é True.', False),
                        ('c', 'pode_entrar é False.', True),
                        ('d', 'pode_entrar é True.', False),
                    ),
                ),
                ('Há só crachá. Entra?', 'Sim', 'Não', 'b'),
                ('Há só senha. Entra?', 'Sim', 'Não', 'b'),
            ),
        ),
        (
            'Cadastro completo',
            'Verificar requisitos simultâneos',
            (
                ('Exige nome e e-mail; há os dois. Conclui?', 'Sim', 'Não', 'a'),
                ('Há nome, mas falta e-mail. Conclui?', 'Sim', 'Não', 'b'),
                ('Há e-mail, mas falta nome. Conclui?', 'Sim', 'Não', 'b'),
            ),
        ),
        (
            'Alternativas de entrada',
            'Praticar disjunção',
            (
                ('Aceita QR ou cartão; há QR. Entra?', 'Sim', 'Não', 'a'),
                ('Há cartão, mas não QR. Entra?', 'Sim', 'Não', 'a'),
                ('Não há QR nem cartão. Entra?', 'Sim', 'Não', 'b'),
            ),
        ),
        (
            'Contato disponível',
            'Usar uma de duas alternativas',
            (
                ('Basta telefone ou e-mail; há telefone. Contata?', 'Sim', 'Não', 'a'),
                ('Há só e-mail. Contata?', 'Sim', 'Não', 'a'),
                ('Não há nenhum contato. Contata?', 'Sim', 'Não', 'b'),
            ),
        ),
        (
            'Permissão com bloqueio',
            'Combinar E, OU e NÃO',
            (
                (
                    'Aceita cartão ou QR, mas bloqueio impede; há QR e bloqueio. Entra?',
                    'Sim',
                    'Não',
                    'b',
                ),
                ('Há cartão e nenhum bloqueio. Entra?', 'Sim', 'Não', 'a'),
                ('Não há cartão nem QR, e não há bloqueio. Entra?', 'Sim', 'Não', 'b'),
            ),
        ),
        (
            'Regra de envio',
            'Resolver expressão composta',
            (
                (
                    'Envia com e-mail verificado e consentimento; há ambos. Envia?',
                    'Sim',
                    'Não',
                    'a',
                ),
                (
                    'Há consentimento, mas e-mail não verificado. Envia?',
                    'Sim',
                    'Não',
                    'b',
                ),
                (
                    'Há e-mail verificado, mas consentimento foi revogado. Envia?',
                    'Sim',
                    'Não',
                    'b',
                ),
            ),
        ),
    )
    priority = (
        (
            'Diagnóstico: urgência',
            'Reconhecer uma prioridade',
            (
                (
                    'Urgência passa antes da ordem de chegada. Quem segue?',
                    'Urgente',
                    'Primeiro da fila',
                    'a',
                ),
            ),
        ),
        (
            'Diagnóstico: exceção VIP',
            'Aplicar uma exceção',
            (
                (
                    'Regra VIP substitui a comum; ambas valem. Qual usar?',
                    'VIP',
                    'Comum',
                    'a',
                ),
            ),
        ),
        (
            'Diagnóstico: bloqueio final',
            'Resolver regras concorrentes',
            (
                (
                    'Bloqueio impede acesso até para VIP. VIP bloqueado entra?',
                    'Entra',
                    'Não entra',
                    'b',
                ),
            ),
        ),
        (
            'Prioridade de atendimento',
            'Escolher a fila prioritária',
            (
                ('Há um caso urgente e um comum. Quem segue?', 'Urgente', 'Comum', 'a'),
                ('Sem urgentes, quem segue?', 'Primeiro comum', 'Último comum', 'a'),
                (
                    'Urgente chegou depois. Quem segue?',
                    'Urgente',
                    'Primeiro comum',
                    'a',
                ),
            ),
        ),
        (
            'Ordem com exceção',
            'Aplicar prioridade condicional',
            (
                (
                    'Regra: VIP antes do comum. Há VIP e comum. Quem segue?',
                    'VIP',
                    'Comum',
                    'a',
                ),
                ('Não há VIP. Quem segue?', 'Comum', 'Ninguém', 'a'),
                ('VIP chegou depois do comum. Quem segue?', 'VIP', 'Comum', 'a'),
            ),
        ),
        (
            'Cupons concorrentes',
            'Distinguir regra especial',
            (
                (
                    'Cupom especial substitui comum; há ambos. Qual vale?',
                    'Especial',
                    'Comum',
                    'a',
                ),
                ('Sem especial, há comum. Qual vale?', 'Comum', 'Nenhum', 'a'),
                (
                    'Especial expirou, comum está válido. Qual vale?',
                    'Especial',
                    'Comum',
                    'b',
                ),
            ),
        ),
        (
            'Escala de incidentes',
            'Ordenar categorias',
            (
                (
                    'Crítico antes de alto; há ambos. Qual segue?',
                    'Crítico',
                    'Alto',
                    'a',
                ),
                ('Alto antes de comum; há ambos. Qual segue?', 'Alto', 'Comum', 'a'),
                ('Sem crítico nem alto, qual segue?', 'Comum', 'Nenhum', 'a'),
            ),
        ),
        (
            'Bloqueio acima do benefício',
            'Aplicar uma proibição prioritária',
            (
                ('Bloqueio supera VIP; VIP bloqueado entra?', 'Sim', 'Não', 'b'),
                ('VIP sem bloqueio entra antes do comum?', 'Sim', 'Não', 'a'),
                ('Comum bloqueado entra?', 'Sim', 'Não', 'b'),
            ),
        ),
        (
            'Exceções em cascata',
            'Resolver prioridade e impedimento',
            (
                (
                    'Emergência supera fila; emergência chegou depois. Quem segue?',
                    'Emergência',
                    'Fila',
                    'a',
                ),
                (
                    'Bloqueio supera emergência; emergência bloqueada entra?',
                    'Sim',
                    'Não',
                    'b',
                ),
                ('Sem emergência, a fila segue ordem de chegada?', 'Sim', 'Não', 'a'),
            ),
        ),
    )
    levels = (
        ActivityDifficulty.EASY,
        ActivityDifficulty.MEDIUM,
        ActivityDifficulty.HARD,
        ActivityDifficulty.EASY,
        ActivityDifficulty.EASY,
        ActivityDifficulty.MEDIUM,
        ActivityDifficulty.MEDIUM,
        ActivityDifficulty.HARD,
        ActivityDifficulty.HARD,
    )
    result: list[Activity] = []
    for competency_id, concept_id, ids, scenarios, prerequisites in (
        (
            SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            SEED_ADAPTIVE_LAB_CONDITIONS_CONCEPT_ID,
            SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS,
            conditions,
            (),
        ),
        (
            SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            SEED_ADAPTIVE_LAB_BOOLEAN_CONCEPT_ID,
            SEED_ADAPTIVE_LAB_BOOLEAN_ACTIVITY_IDS,
            boolean,
            (SEED_ADAPTIVE_LAB_CONDITIONS_CONCEPT_ID,),
        ),
        (
            SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID,
            SEED_ADAPTIVE_LAB_PRIORITY_CONCEPT_ID,
            SEED_ADAPTIVE_LAB_PRIORITY_ACTIVITY_IDS,
            priority,
            (SEED_ADAPTIVE_LAB_CONDITIONS_CONCEPT_ID,),
        ),
    ):
        for index, (activity_id, difficulty, scenario) in enumerate(
            zip(ids, levels, scenarios, strict=True)
        ):
            title, objective, items = scenario
            is_diagnostic = index < 3
            result.append(
                _adaptive_choice_activity(
                    activity_id=activity_id,
                    competency_id=competency_id,
                    concept_id=concept_id,
                    activity_type=(
                        ActivityType.DIAGNOSTIC
                        if is_diagnostic
                        else ActivityType.LEARNING
                    ),
                    difficulty=difficulty,
                    title=title,
                    objective=objective,
                    items=items,
                    required_concept_ids=() if is_diagnostic else prerequisites,
                )
            )
    return tuple(result)


def build_development_seed() -> DevelopmentSeed:
    account = AccountFaker.fake(
        id=SEED_ACCOUNT_ID,
        display_name='Pessoa Estudante',
        email='student.seed@shifu.com',
        password_hash=Argon2idHashProvider().hash(SEED_ACCOUNT_PASSWORD),
        access_version=1,
        time_zone='America/Sao_Paulo',
        created_at=SEED_CREATED_AT,
        updated_at=SEED_CREATED_AT,
        confirmed_at=SEED_CREATED_AT,
    )

    skills = (
        SkillFaker.fake(
            id=SEED_SKILL_LOGIC_ID,
            name='Lógica de programação',
            description='Fundamentos para resolver problemas com algoritmos.',
        ),
        SkillFaker.fake(
            id=SEED_SKILL_PYTHON_ID,
            name='Python essencial',
            description='Sintaxe e estruturas básicas para criar programas em Python.',
        ),
        Skill(
            id=SEED_ADAPTIVE_SKILL_ID,
            name='Decisões em algoritmos',
            description='Prática de condições com diagnóstico e evidência por Conceito.',
        ),
        Skill(
            id=SEED_ADAPTIVE_LAB_SKILL_ID,
            name='Laboratório de decisões adaptativas',
            description='Explore diagnóstico, pré-requisitos, cobertura, domínio e regressão em duas Competências.',
        ),
        Skill(
            id=SEED_GRAPH_DATA_STRUCTURES_SKILL_ID,
            name='Estruturas de dados',
            description='Organize coleções para consultar e transformar informações.',
        ),
        Skill(
            id=SEED_GRAPH_SEARCH_SKILL_ID,
            name='Algoritmos de busca',
            description='Encontre elementos e compare estratégias de busca.',
        ),
        Skill(
            id=SEED_GRAPH_DATA_MODELING_SKILL_ID,
            name='Modelagem de dados',
            description='Estruture informações para aplicações persistentes.',
        ),
        Skill(
            id=SEED_GRAPH_APIS_SKILL_ID,
            name='APIs web',
            description='Conecte dados e regras por interfaces HTTP.',
        ),
        Skill(
            id=SEED_GRAPH_TESTING_SKILL_ID,
            name='Testes automatizados',
            description='Verifique o comportamento de programas com testes.',
        ),
        Skill(
            id=SEED_GRAPH_PROJECT_SKILL_ID,
            name='Projeto integrador',
            description='Combine fundamentos, dados, APIs e testes em uma aplicação.',
        ),
    )
    skill_foundations = (
        SkillFoundation(
            skill_id=SEED_SKILL_PYTHON_ID,
            foundation_skill_id=SEED_SKILL_LOGIC_ID,
        ),
        SkillFoundation(
            skill_id=SEED_ADAPTIVE_SKILL_ID,
            foundation_skill_id=SEED_SKILL_LOGIC_ID,
        ),
        SkillFoundation(
            skill_id=SEED_GRAPH_DATA_STRUCTURES_SKILL_ID,
            foundation_skill_id=SEED_SKILL_LOGIC_ID,
        ),
        SkillFoundation(
            skill_id=SEED_ADAPTIVE_LAB_SKILL_ID,
            foundation_skill_id=SEED_ADAPTIVE_SKILL_ID,
        ),
        SkillFoundation(
            skill_id=SEED_GRAPH_SEARCH_SKILL_ID,
            foundation_skill_id=SEED_GRAPH_DATA_STRUCTURES_SKILL_ID,
        ),
        SkillFoundation(
            skill_id=SEED_GRAPH_DATA_MODELING_SKILL_ID,
            foundation_skill_id=SEED_SKILL_PYTHON_ID,
        ),
        SkillFoundation(
            skill_id=SEED_GRAPH_APIS_SKILL_ID,
            foundation_skill_id=SEED_SKILL_PYTHON_ID,
        ),
        SkillFoundation(
            skill_id=SEED_GRAPH_APIS_SKILL_ID,
            foundation_skill_id=SEED_GRAPH_DATA_MODELING_SKILL_ID,
        ),
        SkillFoundation(
            skill_id=SEED_GRAPH_TESTING_SKILL_ID,
            foundation_skill_id=SEED_SKILL_PYTHON_ID,
        ),
        SkillFoundation(
            skill_id=SEED_GRAPH_PROJECT_SKILL_ID,
            foundation_skill_id=SEED_GRAPH_SEARCH_SKILL_ID,
        ),
        SkillFoundation(
            skill_id=SEED_GRAPH_PROJECT_SKILL_ID,
            foundation_skill_id=SEED_ADAPTIVE_LAB_SKILL_ID,
        ),
        SkillFoundation(
            skill_id=SEED_GRAPH_PROJECT_SKILL_ID,
            foundation_skill_id=SEED_GRAPH_APIS_SKILL_ID,
        ),
        SkillFoundation(
            skill_id=SEED_GRAPH_PROJECT_SKILL_ID,
            foundation_skill_id=SEED_GRAPH_TESTING_SKILL_ID,
        ),
    )
    competencies = (
        CompetencyFaker.fake(
            id=SEED_COMPETENCY_VARIABLES_ID,
            skill_id=SEED_SKILL_LOGIC_ID,
            name='Variáveis e valores',
            description='Representar valores e atualizar seu estado.',
            position=1,
        ),
        CompetencyFaker.fake(
            id=SEED_COMPETENCY_CONDITIONS_ID,
            skill_id=SEED_SKILL_LOGIC_ID,
            name='Condições',
            description='Escolher caminhos diferentes durante a execução.',
            position=3,
        ),
        CompetencyFaker.fake(
            id=SEED_COMPETENCY_REPETITION_ID,
            skill_id=SEED_SKILL_LOGIC_ID,
            name='Estruturas de repetição',
            description='Repetir instruções com controle e previsibilidade.',
            position=2,
        ),
        CompetencyFaker.fake(
            id=SEED_COMPETENCY_FUNCTIONS_ID,
            skill_id=SEED_SKILL_PYTHON_ID,
            name='Funções',
            description='Organizar lógica reutilizável em funções Python.',
            position=1,
        ),
        Competency(
            id=SEED_ADAPTIVE_COMPETENCY_ID,
            skill_id=SEED_ADAPTIVE_SKILL_ID,
            name='Escolher caminhos',
            description='Aplicar condições para escolher o ramo de um algoritmo.',
            position=1,
        ),
        Competency(
            id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            skill_id=SEED_ADAPTIVE_LAB_SKILL_ID,
            name='Interpretar condições',
            description='Comparar valores, aplicar limites e combinar requisitos.',
            position=1,
        ),
        Competency(
            id=SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID,
            skill_id=SEED_ADAPTIVE_LAB_SKILL_ID,
            name='Resolver prioridades',
            description='Escolher regras especiais, prioridades e bloqueios.',
            position=2,
        ),
    )
    concepts = (
        Concept(
            id=SEED_ADAPTIVE_CONCEPT_ID,
            competency_id=SEED_ADAPTIVE_COMPETENCY_ID,
            name='Avaliar condições',
            description='Determinar o ramo executado por condições explícitas.',
            position=1,
            observation_criteria='A resposta identifica o ramo executado com base nas condições e prioridades declaradas.',
        ),
        Concept(
            id=SEED_ADAPTIVE_LAB_CONDITIONS_CONCEPT_ID,
            competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            name='Condições e limites',
            description='Avaliar comparações, limites inclusivos e requisitos combinados.',
            position=1,
            observation_criteria='A resposta identifica corretamente o resultado de uma condição explícita.',
        ),
        Concept(
            id=SEED_ADAPTIVE_LAB_BOOLEAN_CONCEPT_ID,
            competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            name='Combinação e negação',
            description='Aplicar E, OU e NÃO em regras com requisitos e impedimentos.',
            position=2,
            observation_criteria='A resposta avalia corretamente a combinação de condições e bloqueios.',
            prerequisite_ids=(SEED_ADAPTIVE_LAB_CONDITIONS_CONCEPT_ID,),
        ),
        Concept(
            id=SEED_ADAPTIVE_LAB_PRIORITY_CONCEPT_ID,
            competency_id=SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID,
            name='Prioridades e exceções',
            description='Resolver regras concorrentes após interpretar suas condições.',
            position=1,
            observation_criteria='A resposta aplica a prioridade ou o impedimento declarado.',
            prerequisite_ids=(SEED_ADAPTIVE_LAB_BOOLEAN_CONCEPT_ID,),
        ),
    )
    materials = (
        MaterialFaker.fake(
            id=SEED_MATERIAL_LOGIC_ID,
            skill_id=SEED_SKILL_LOGIC_ID,
            title='Introdução aos algoritmos',
            content='Um algoritmo descreve passos finitos para resolver um problema.',
        ),
        MaterialFaker.fake(
            id=SEED_MATERIAL_PYTHON_ID,
            skill_id=SEED_SKILL_PYTHON_ID,
            title='Primeiros passos com Python',
            content='Python permite expressar soluções com uma sintaxe direta e legível.',
        ),
        MaterialFaker.fake(
            id=SEED_MATERIAL_REPETITION_INTRO_ID,
            skill_id=SEED_SKILL_LOGIC_ID,
            title='Por que repetir instruções?',
            content='Estruturas de repetição automatizam passos que seguem um padrão.',
            material_type=MaterialType.THEORY,
        ),
        MaterialFaker.fake(
            id=SEED_MATERIAL_REPETITION_FOR_ID,
            skill_id=SEED_SKILL_LOGIC_ID,
            title='Repetição com for',
            content='O laço for percorre uma sequência de valores de forma previsível.',
            material_type=MaterialType.REFERENCE,
        ),
        Material(
            id=SEED_ADAPTIVE_MATERIAL_ID,
            skill_id=SEED_ADAPTIVE_SKILL_ID,
            title='Como avaliar uma condição',
            content='Leia a regra e seus limites; verifique cada condição e, quando houver exceções, aplique a prioridade declarada antes de escolher o ramo.',
            material_type=MaterialType.THEORY,
            concept_ids=(SEED_ADAPTIVE_CONCEPT_ID,),
        ),
        Material(
            id=SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID,
            skill_id=SEED_ADAPTIVE_LAB_SKILL_ID,
            title='Condições, limites e combinações',
            content='Compare o valor com o limite e verifique se o limite é inclusivo. Em uma regra com "e", todos os requisitos devem ser verdadeiros; uma negação impede o resultado quando a condição negada ocorre.',
            material_type=MaterialType.THEORY,
            concept_ids=(SEED_ADAPTIVE_LAB_CONDITIONS_CONCEPT_ID,),
        ),
        Material(
            id=SEED_ADAPTIVE_LAB_BOOLEAN_MATERIAL_ID,
            skill_id=SEED_ADAPTIVE_LAB_SKILL_ID,
            title='Como combinar condições',
            content='Na regra E, todos os requisitos precisam valer. Na regra OU, basta uma alternativa. Na regra NÃO, a condição negada impede o resultado mesmo quando há outros requisitos satisfeitos.',
            material_type=MaterialType.THEORY,
            concept_ids=(SEED_ADAPTIVE_LAB_BOOLEAN_CONCEPT_ID,),
        ),
        Material(
            id=SEED_ADAPTIVE_LAB_PRIORITY_MATERIAL_ID,
            skill_id=SEED_ADAPTIVE_LAB_SKILL_ID,
            title='Prioridades, exceções e bloqueios',
            content='Primeiro identifique as condições de cada regra. Depois aplique a ordem de prioridade declarada: uma exceção substitui a regra comum, mas um bloqueio explícito pode impedir até a exceção.',
            material_type=MaterialType.THEORY,
            concept_ids=(SEED_ADAPTIVE_LAB_PRIORITY_CONCEPT_ID,),
        ),
    )
    activities = (
        ActivityFaker.fake(
            id=SEED_ACTIVITY_VARIABLES_ID,
            competency_id=SEED_COMPETENCY_VARIABLES_ID,
            title='Nomeie os valores do algoritmo',
            objective='Reconhecer o papel de uma variável em um algoritmo.',
            difficulty=ActivityDifficulty.HARD,
        ),
        ActivityFaker.fake(
            id=SEED_ACTIVITY_CONDITIONS_ID,
            competency_id=SEED_COMPETENCY_CONDITIONS_ID,
            title='Escolha o caminho correto',
            objective='Identificar quando uma condição deve ser aplicada.',
            difficulty=ActivityDifficulty.HARD,
        ),
        ActivityFaker.fake(
            id=SEED_ACTIVITY_FUNCTIONS_ID,
            competency_id=SEED_COMPETENCY_FUNCTIONS_ID,
            title='Extraia uma função',
            objective='Reconhecer uma oportunidade de reutilizar lógica em Python.',
        ),
        ActivityFaker.fake(
            id=SEED_ACTIVITY_REPETITION_EASY_ID,
            competency_id=SEED_COMPETENCY_REPETITION_ID,
            title='Repita os passos básicos',
            objective='Identificar quando uma repetição simples resolve um problema.',
            difficulty=ActivityDifficulty.EASY,
        ),
        ActivityFaker.fake(
            id=SEED_ACTIVITY_REPETITION_MEDIUM_ID,
            competency_id=SEED_COMPETENCY_REPETITION_ID,
            title='Controle a condição de parada',
            objective='Escolher uma condição de parada para um laço.',
            difficulty=ActivityDifficulty.MEDIUM,
        ),
        ActivityFaker.fake(
            id=SEED_ACTIVITY_REPETITION_HARD_ID,
            competency_id=SEED_COMPETENCY_REPETITION_ID,
            title='Combine estruturas de repetição',
            objective='Resolver um problema usando estruturas de repetição.',
            difficulty=ActivityDifficulty.HARD,
        ),
        *_adaptive_activities(),
        *_adaptive_lab_activities(),
    )
    curriculum_sequences = (
        CurriculumSequence(
            competency_id=SEED_COMPETENCY_VARIABLES_ID,
            items=(
                MaterialSequenceItem(position=1, material_id=SEED_MATERIAL_LOGIC_ID),
                ActivitySequenceItem(
                    position=2, activity_id=SEED_ACTIVITY_VARIABLES_ID
                ),
            ),
        ),
        CurriculumSequence(
            competency_id=SEED_COMPETENCY_CONDITIONS_ID,
            items=(
                ActivitySequenceItem(
                    position=1, activity_id=SEED_ACTIVITY_CONDITIONS_ID
                ),
            ),
        ),
        CurriculumSequence(
            competency_id=SEED_COMPETENCY_REPETITION_ID,
            items=(
                MaterialSequenceItem(
                    position=1,
                    material_id=SEED_MATERIAL_REPETITION_INTRO_ID,
                ),
                ActivitySequenceItem(
                    position=2,
                    activity_id=SEED_ACTIVITY_REPETITION_EASY_ID,
                ),
                MaterialSequenceItem(
                    position=3,
                    material_id=SEED_MATERIAL_REPETITION_FOR_ID,
                ),
                ActivitySequenceItem(
                    position=4,
                    activity_id=SEED_ACTIVITY_REPETITION_MEDIUM_ID,
                ),
                ActivitySequenceItem(
                    position=5,
                    activity_id=SEED_ACTIVITY_REPETITION_HARD_ID,
                ),
            ),
        ),
        CurriculumSequence(
            competency_id=SEED_COMPETENCY_FUNCTIONS_ID,
            items=(
                MaterialSequenceItem(position=1, material_id=SEED_MATERIAL_PYTHON_ID),
                ActivitySequenceItem(
                    position=2, activity_id=SEED_ACTIVITY_FUNCTIONS_ID
                ),
            ),
        ),
        CurriculumSequence(
            competency_id=SEED_ADAPTIVE_COMPETENCY_ID,
            items=(
                MaterialSequenceItem(position=1, material_id=SEED_ADAPTIVE_MATERIAL_ID),
                *(
                    ActivitySequenceItem(position=position, activity_id=activity_id)
                    for position, activity_id in enumerate(
                        SEED_ADAPTIVE_ACTIVITY_IDS[3:], start=2
                    )
                ),
            ),
        ),
        CurriculumSequence(
            competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            items=(
                MaterialSequenceItem(
                    position=1, material_id=SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID
                ),
                *(
                    ActivitySequenceItem(position=position, activity_id=activity_id)
                    for position, activity_id in enumerate(
                        SEED_ADAPTIVE_LAB_CONDITIONS_ACTIVITY_IDS[3:], start=2
                    )
                ),
                MaterialSequenceItem(
                    position=8, material_id=SEED_ADAPTIVE_LAB_BOOLEAN_MATERIAL_ID
                ),
                *(
                    ActivitySequenceItem(position=position, activity_id=activity_id)
                    for position, activity_id in enumerate(
                        SEED_ADAPTIVE_LAB_BOOLEAN_ACTIVITY_IDS[3:], start=9
                    )
                ),
            ),
        ),
        CurriculumSequence(
            competency_id=SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID,
            items=(
                MaterialSequenceItem(
                    position=1, material_id=SEED_ADAPTIVE_LAB_PRIORITY_MATERIAL_ID
                ),
                *(
                    ActivitySequenceItem(position=position, activity_id=activity_id)
                    for position, activity_id in enumerate(
                        SEED_ADAPTIVE_LAB_PRIORITY_ACTIVITY_IDS[3:], start=2
                    )
                ),
            ),
        ),
    )

    goals = (
        GoalFaker.fake(
            id=SEED_GOAL_ID,
            account_id=SEED_ACCOUNT_ID,
            title='Aprender a programar',
            description='Construir uma base prática para resolver problemas com código.',
            created_at=SEED_CREATED_AT,
            updated_at=SEED_CREATED_AT,
        ),
        Goal(
            id=SEED_ADAPTIVE_LAB_GOAL_ID,
            account_id=SEED_ACCOUNT_ID,
            title='Laboratório de progresso adaptativo',
            description='Comece pelo diagnóstico e acompanhe a evolução de duas Competências.',
            created_at=SEED_CREATED_AT,
            updated_at=SEED_CREATED_AT,
        ),
        Goal(
            id=SEED_GRAPH_GOAL_ID,
            account_id=SEED_ACCOUNT_ID,
            title='Mapa de desenvolvimento de software',
            description='Explore uma trilha de programação com fundamentos, ramificações e caminhos que se encontram em um projeto.',
            created_at=SEED_CREATED_AT,
            updated_at=SEED_CREATED_AT,
        ),
    )
    skill_experiences = (
        SkillExperienceFaker.fake(
            id=SEED_LOGIC_EXPERIENCE_ID,
            goal_id=SEED_GOAL_ID,
            skill_id=SEED_SKILL_LOGIC_ID,
            inclusion_reason='Fundamento para todo o restante do percurso.',
            status=SkillExperienceStatus.LEARNING,
            created_at=SEED_CREATED_AT,
            updated_at=SEED_CREATED_AT,
        ),
        SkillExperienceFaker.fake(
            id=SEED_PYTHON_EXPERIENCE_ID,
            goal_id=SEED_GOAL_ID,
            skill_id=SEED_SKILL_PYTHON_ID,
            inclusion_reason='Aplicar a lógica em uma linguagem prática.',
            status=SkillExperienceStatus.NOT_STARTED,
            created_at=SEED_CREATED_AT,
            updated_at=SEED_CREATED_AT,
        ),
        SkillExperience(
            id=SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
            goal_id=SEED_ADAPTIVE_LAB_GOAL_ID,
            skill_id=SEED_ADAPTIVE_LAB_SKILL_ID,
            inclusion_reason='Explorar diagnóstico, evidência por Conceito e recomendações.',
            status=SkillExperienceStatus.NOT_STARTED,
            created_at=SEED_CREATED_AT,
            updated_at=SEED_CREATED_AT,
            policy_id=AdaptiveLearningPolicy.policy_id,
        ),
        *(
            SkillExperience(
                id=experience_id,
                goal_id=SEED_GRAPH_GOAL_ID,
                skill_id=skill_id,
                inclusion_reason=None,
                status=SkillExperienceStatus.NOT_STARTED,
                created_at=SEED_CREATED_AT,
                updated_at=SEED_CREATED_AT,
            )
            for experience_id, skill_id in zip(
                SEED_GRAPH_EXPERIENCE_IDS, SEED_GRAPH_SKILL_IDS, strict=True
            )
        ),
    )
    competency_progresses = (
        CompetencyProgressFaker.fake(
            id=SEED_PROGRESS_ID,
            skill_experience_id=SEED_LOGIC_EXPERIENCE_ID,
            competency_id=SEED_COMPETENCY_VARIABLES_ID,
            status=CompetencyProgressStatus.MASTERED,
            hard_activity_score=Decimal('100'),
            created_at=SEED_CREATED_AT,
            updated_at=SEED_CREATED_AT,
        ),
        CompetencyProgressFaker.fake(
            id=SEED_REPETITION_PROGRESS_ID,
            skill_experience_id=SEED_LOGIC_EXPERIENCE_ID,
            competency_id=SEED_COMPETENCY_REPETITION_ID,
            status=CompetencyProgressStatus.DEVELOPING,
            current_progress=Decimal('55'),
            initial_progress=Decimal('35'),
            created_at=SEED_CREATED_AT,
            updated_at=SEED_CREATED_AT,
        ),
        CompetencyProgressFaker.fake(
            id=SEED_CONDITIONS_PROGRESS_ID,
            skill_experience_id=SEED_LOGIC_EXPERIENCE_ID,
            competency_id=SEED_COMPETENCY_CONDITIONS_ID,
            status=CompetencyProgressStatus.MASTERED,
            hard_activity_score=Decimal('100'),
            created_at=SEED_CREATED_AT,
            updated_at=SEED_CREATED_AT,
        ),
        CompetencyProgress(
            id=SEED_ADAPTIVE_LAB_CONDITIONS_PROGRESS_ID,
            skill_experience_id=SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
            competency_id=SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            content_released=False,
            created_at=SEED_CREATED_AT,
            updated_at=SEED_CREATED_AT,
            status=CompetencyProgressStatus.LEARNING,
        ),
        CompetencyProgress(
            id=SEED_ADAPTIVE_LAB_PRIORITY_PROGRESS_ID,
            skill_experience_id=SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
            competency_id=SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID,
            content_released=False,
            created_at=SEED_CREATED_AT,
            updated_at=SEED_CREATED_AT,
            status=CompetencyProgressStatus.LEARNING,
        ),
    )
    activity_attempts = (
        ActivityAttemptFaker.fake(
            id=SEED_ATTEMPT_ID,
            skill_experience_id=SEED_LOGIC_EXPERIENCE_ID,
            competency_id=SEED_COMPETENCY_VARIABLES_ID,
            activity_id=SEED_ACTIVITY_VARIABLES_ID,
            kind=ActivityAttemptKind.LEARNING,
            submitted_at=SEED_CREATED_AT,
        ),
        ActivityAttemptFaker.fake(
            id=SEED_REPETITION_ATTEMPT_ID,
            skill_experience_id=SEED_LOGIC_EXPERIENCE_ID,
            competency_id=SEED_COMPETENCY_REPETITION_ID,
            activity_id=SEED_ACTIVITY_REPETITION_EASY_ID,
            kind=ActivityAttemptKind.LEARNING,
            submitted_at=SEED_CREATED_AT,
        ),
        ActivityAttemptFaker.fake(
            id=SEED_CONDITIONS_ATTEMPT_ID,
            skill_experience_id=SEED_LOGIC_EXPERIENCE_ID,
            competency_id=SEED_COMPETENCY_CONDITIONS_ID,
            activity_id=SEED_ACTIVITY_CONDITIONS_ID,
            kind=ActivityAttemptKind.LEARNING,
            submitted_at=SEED_CREATED_AT,
        ),
    )
    activity_evaluations = (
        ActivityEvaluationFaker.fake(
            id=SEED_EVALUATION_ID,
            attempt_id=SEED_ATTEMPT_ID,
            status=ActivityEvaluationStatus.COMPLETED,
            started_at=SEED_CREATED_AT,
            completed_at=SEED_CREATED_AT,
            effect_applied_at=SEED_CREATED_AT,
            score=Decimal('100'),
        ),
        ActivityEvaluationFaker.fake(
            id=SEED_REPETITION_EVALUATION_ID,
            attempt_id=SEED_REPETITION_ATTEMPT_ID,
            status=ActivityEvaluationStatus.COMPLETED,
            started_at=SEED_CREATED_AT,
            completed_at=SEED_CREATED_AT,
            effect_applied_at=SEED_CREATED_AT,
            score=Decimal('65'),
        ),
        ActivityEvaluationFaker.fake(
            id=SEED_CONDITIONS_EVALUATION_ID,
            attempt_id=SEED_CONDITIONS_ATTEMPT_ID,
            status=ActivityEvaluationStatus.COMPLETED,
            started_at=SEED_CREATED_AT,
            completed_at=SEED_CREATED_AT,
            effect_applied_at=SEED_CREATED_AT,
            score=Decimal('100'),
        ),
    )

    communications = (
        Communication(
            id=SEED_COMMUNICATION_ID,
            account_id=SEED_ACCOUNT_ID,
            type=CommunicationType.ACCOUNT_CONFIRMATION,
            channel=CommunicationChannel.EMAIL,
            recipient_email=account.email,
            recipient_name=account.display_name,
            content=MessageContent(
                subject='Confirme seu e-mail no Shifu',
                html='<p>Confirme seu e-mail para continuar aprendendo.</p>',
                text='Confirme seu e-mail para continuar aprendendo.',
            ),
            status=CommunicationStatus.PENDING,
            idempotency_key='seed/account-confirmation/student',
            created_at=SEED_CREATED_AT,
            updated_at=SEED_CREATED_AT,
        ),
    )
    delivery_attempts = (
        DeliveryAttempt(
            id=SEED_DELIVERY_ATTEMPT_ID,
            communication_id=SEED_COMMUNICATION_ID,
            attempt_number=1,
            status=DeliveryAttemptStatus.STARTED,
            attempted_at=SEED_CREATED_AT,
        ),
    )

    return DevelopmentSeed(
        accounts=(account,),
        account_action_tokens=(),
        skills=skills,
        skill_foundations=skill_foundations,
        competencies=competencies,
        concepts=concepts,
        materials=materials,
        activities=activities,
        curriculum_sequences=curriculum_sequences,
        goals=goals,
        skill_experiences=skill_experiences,
        competency_progresses=competency_progresses,
        activity_attempts=activity_attempts,
        activity_evaluations=activity_evaluations,
        communications=communications,
        delivery_attempts=delivery_attempts,
    )

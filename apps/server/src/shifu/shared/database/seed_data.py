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
    CurriculumSequence,
    MaterialSequenceItem,
    SkillFoundation,
)
from shifu.curriculum.core.domain.enums import ActivityDifficulty, MaterialType
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

SEED_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
SEED_ACCOUNT_PASSWORD: str = 'ShifuSeed123!'


@structure
class DevelopmentSeed:
    accounts: tuple[Account, ...]
    account_action_tokens: tuple[AccountActionToken, ...]
    skills: tuple[Skill, ...]
    skill_foundations: tuple[SkillFoundation, ...]
    competencies: tuple[Competency, ...]
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
    )
    skill_foundations = (
        SkillFoundation(
            skill_id=SEED_SKILL_PYTHON_ID,
            foundation_skill_id=SEED_SKILL_LOGIC_ID,
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
            content=(
                'Estruturas de repetição automatizam passos que seguem um padrão.\n'
                'Em vez de escrever a mesma instrução várias vezes, você descreve o\n'
                'passo uma vez e diz quantas vezes ele deve acontecer.\n'
                '\n'
                'Repetir à mão funciona para três itens e falha para mil. O laço\n'
                'mantém o programa legível mesmo quando os dados crescem.\n'
                '\n'
                '```python\n'
                'for numero in [1, 2, 3]:\n'
                '    print(numero)\n'
                '```\n'
                '\n'
                'O bloco acima percorre a lista e executa `print` uma vez para cada\n'
                'elemento.'
            ),
            material_type=MaterialType.THEORY,
        ),
        MaterialFaker.fake(
            id=SEED_MATERIAL_REPETITION_FOR_ID,
            skill_id=SEED_SKILL_LOGIC_ID,
            title='Repetição com for',
            content=(
                'O laço `for` percorre uma sequência de valores de forma previsível.\n'
                'Ele pede à sequência o próximo item até que não exista mais nenhum.\n'
                '\n'
                '```python\n'
                'total = 0\n'
                'for valor in [10, 20, 30]:\n'
                '    total = total + valor\n'
                '```\n'
                '\n'
                'Como o número de passos vem da própria sequência, o laço termina\n'
                'sozinho.'
            ),
            material_type=MaterialType.REFERENCE,
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

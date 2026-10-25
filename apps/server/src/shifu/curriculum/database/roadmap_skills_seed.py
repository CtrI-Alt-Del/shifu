"""Backend roadmap Skills with placeholder content to exercise the Planner.

Every Skill gets the minimum content that makes it startable, so a planned Goal can
be created from any combination; the content itself is marked as "[Teste]".
"""

from collections.abc import Mapping
from dataclasses import dataclass

from shifu.curriculum.core.domain.entities import (
    Activity,
    Competency,
    Concept,
    Material,
    Skill,
)
from shifu.curriculum.core.domain.structures import (
    CurriculumSequence,
    SkillFoundation,
)
from shifu.fakers.curriculum.ready_skill_content_faker import (
    ReadySkillContent,
    ReadySkillContentFaker,
)


@dataclass(frozen=True, slots=True)
class RoadmapSkillsSeed:
    skills: tuple[Skill, ...]
    skill_foundations: tuple[SkillFoundation, ...]
    competencies: tuple[Competency, ...]
    concepts: tuple[Concept, ...]
    materials: tuple[Material, ...]
    activities: tuple[Activity, ...]
    curriculum_sequences: tuple[CurriculumSequence, ...]


@dataclass(frozen=True, slots=True)
class _RoadmapSkill:
    key: str
    name: str
    description: str
    foundations: tuple[str, ...] = ()


# Foundation keys name another roadmap Skill or an anchor passed by the caller.
_ROADMAP_SKILLS = (
    _RoadmapSkill(
        'computer',
        'Como funciona um computador',
        'Processador, memória e como um programa é executado pela máquina.',
    ),
    _RoadmapSkill(
        'linux',
        'Sistemas operacionais e Linux',
        'Processos, arquivos, permissões e o terminal em distribuições Linux.',
        ('computer',),
    ),
    _RoadmapSkill(
        'compiled',
        'Linguagens compiladas e interpretadas',
        'Como compiladores e interpretadores transformam código em execução.',
        ('computer',),
    ),
    _RoadmapSkill(
        'procedural',
        'Programação procedural',
        'Organizar programas em procedimentos, variáveis e fluxo de controle.',
        ('logic',),
    ),
    _RoadmapSkill(
        'functional',
        'Programação funcional',
        'Funções puras, imutabilidade e composição de funções.',
        ('logic',),
    ),
    _RoadmapSkill(
        'oop',
        'Programação orientada a objetos',
        'Classes, objetos, abstração, encapsulamento, herança e polimorfismo.',
        ('logic',),
    ),
    _RoadmapSkill(
        'python',
        'Python essencial',
        'Sintaxe, tipos e estruturas básicas para criar programas em Python.',
        ('logic',),
    ),
    _RoadmapSkill(
        'java',
        'Java essencial',
        'Sintaxe, tipos e coleções para criar programas em Java.',
        ('oop',),
    ),
    _RoadmapSkill(
        'csharp',
        'C# essencial',
        'Sintaxe, tipos e coleções para criar programas em C# e .NET.',
        ('oop',),
    ),
    _RoadmapSkill(
        'go',
        'Go essencial',
        'Sintaxe, tipos e concorrência básica para criar programas em Go.',
        ('logic',),
    ),
    _RoadmapSkill(
        'php',
        'PHP essencial',
        'Sintaxe e recursos básicos para criar aplicações web em PHP.',
        ('logic',),
    ),
    _RoadmapSkill(
        'ruby',
        'Ruby essencial',
        'Sintaxe, blocos e coleções para criar programas em Ruby.',
        ('logic',),
    ),
    _RoadmapSkill(
        'rust',
        'Rust essencial',
        'Posse, empréstimos e tipos para criar programas seguros em Rust.',
        ('logic', 'compiled'),
    ),
    _RoadmapSkill(
        'cpp',
        'C++ essencial',
        'Ponteiros, memória e classes para criar programas em C++.',
        ('logic', 'compiled'),
    ),
    _RoadmapSkill(
        'sql',
        'SQL e bancos relacionais',
        'Consultas, junções e operações de CRUD em bancos como PostgreSQL e MySQL.',
        ('logic',),
    ),
    _RoadmapSkill(
        'transactions',
        'Transações e ACID',
        'Atomicidade, consistência, isolamento e durabilidade em bancos relacionais.',
        ('sql',),
    ),
    _RoadmapSkill(
        'nosql',
        'Bancos não relacionais',
        'Bancos de documentos, chave-valor, grafos e busca, como MongoDB e Redis.',
        ('sql',),
    ),
    _RoadmapSkill(
        'git',
        'Versionamento com Git',
        'Commits, branches, merges e histórico de código com Git.',
        ('logic',),
    ),
    _RoadmapSkill(
        'remote_repositories',
        'Repositórios remotos',
        'Colaborar com pull requests no GitHub, GitLab e Bitbucket.',
        ('git',),
    ),
    _RoadmapSkill(
        'internet',
        'Como a internet funciona',
        'Cliente e servidor, DNS, domínios, URLs e servidores web.',
        ('computer',),
    ),
    _RoadmapSkill(
        'http',
        'Protocolo HTTP',
        'Métodos, códigos de status, cabeçalhos, cache e HTTPS.',
        ('internet',),
    ),
    _RoadmapSkill(
        'web_security',
        'Segurança na web',
        'CORS, cookies, sessões, firewall, VPN e ataques comuns como SQL Injection.',
        ('http',),
    ),
    _RoadmapSkill(
        'auth',
        'Autenticação e autorização',
        'Sistemas de login, sessões, tokens e controle de permissões.',
        ('web_security',),
    ),
    _RoadmapSkill(
        'rest',
        'APIs REST',
        'Recursos, JSON, paginação, filtros, versionamento e HATEOAS.',
        ('http', 'apis'),
    ),
    _RoadmapSkill(
        'graphql',
        'GraphQL',
        'Esquemas, consultas e mutações para APIs com GraphQL.',
        ('rest',),
    ),
    _RoadmapSkill(
        'grpc',
        'gRPC',
        'Contratos com Protocol Buffers e comunicação entre serviços com gRPC.',
        ('rest',),
    ),
    _RoadmapSkill(
        'mvc',
        'Padrão MVC',
        'Separar modelo, visão e controlador em aplicações web.',
        ('oop',),
    ),
    _RoadmapSkill(
        'laravel',
        'Laravel',
        'Rotas, controladores e Eloquent para aplicações web em PHP.',
        ('php', 'mvc'),
    ),
    _RoadmapSkill(
        'django',
        'Django',
        'Modelos, views e templates para aplicações web em Python.',
        ('python', 'mvc'),
    ),
    _RoadmapSkill(
        'flask',
        'Flask',
        'Rotas e extensões para criar APIs leves em Python.',
        ('python', 'rest'),
    ),
    _RoadmapSkill(
        'spring',
        'Spring Boot',
        'Injeção de dependências e APIs REST em Java com Spring Boot.',
        ('java', 'mvc'),
    ),
    _RoadmapSkill(
        'nestjs',
        'NestJS',
        'Módulos, controladores e provedores para APIs em Node.js com NestJS.',
        ('javascript', 'mvc'),
    ),
    _RoadmapSkill(
        'rails',
        'Ruby on Rails',
        'Convenções, Active Record e aplicações web completas em Ruby.',
        ('ruby', 'mvc'),
    ),
    _RoadmapSkill(
        'aspnet',
        'ASP.NET',
        'Controladores, middlewares e APIs web em C# com ASP.NET.',
        ('csharp', 'mvc'),
    ),
    _RoadmapSkill(
        'docker',
        'Docker',
        'Contêineres, imagens, volumes, redes e Dockerfile.',
        ('linux',),
    ),
    _RoadmapSkill(
        'docker_compose',
        'Docker Compose',
        'Orquestrar vários contêineres de uma aplicação com Docker Compose.',
        ('docker',),
    ),
    _RoadmapSkill(
        'clean_code',
        'Clean Code',
        'Nomes significativos, funções pequenas, DRY, KISS e YAGNI.',
        ('oop',),
    ),
    _RoadmapSkill(
        'solid',
        'Princípios SOLID',
        'Responsabilidade única, aberto e fechado, Liskov, interfaces e dependências.',
        ('oop',),
    ),
    _RoadmapSkill(
        'calisthenics',
        'Object Calisthenics',
        'Regras para classes coesas: sem ELSE, tipos primitivos envolvidos e sem getters.',
        ('clean_code',),
    ),
    _RoadmapSkill(
        'design_patterns',
        'Design Patterns',
        'Padrões criacionais, estruturais e comportamentais do catálogo GoF.',
        ('solid',),
    ),
    _RoadmapSkill(
        'refactoring',
        'Refatoração e code smells',
        'Identificar code smells e débito técnico e aplicar técnicas de refatoração.',
        ('clean_code',),
    ),
    _RoadmapSkill(
        'testing',
        'Testes automatizados',
        'Escrever testes unitários e de integração que verificam o comportamento.',
        ('logic',),
    ),
    _RoadmapSkill(
        'test_pyramid',
        'Pirâmide de testes',
        'Equilibrar testes unitários, de integração e funcionais.',
        ('testing',),
    ),
    _RoadmapSkill(
        'performance',
        'Cache e performance',
        'Cache Aside, CDN, jobs assíncronos e otimização de consultas SQL.',
        ('rest', 'sql'),
    ),
    _RoadmapSkill(
        'ci_cd',
        'Pipelines de CI/CD',
        'Automatizar testes e entregas com GitHub Actions, GitLab CI e Jenkins.',
        ('remote_repositories', 'test_pyramid'),
    ),
    _RoadmapSkill(
        'cloud',
        'Fundamentos de cloud',
        'Serviços básicos de computação, armazenamento e rede em provedores de nuvem.',
        ('docker',),
    ),
    _RoadmapSkill(
        'requirements',
        'Requisitos funcionais e não funcionais',
        'Descrever o que o sistema faz e suas metas de qualidade, como desempenho.',
    ),
    _RoadmapSkill(
        'ddd',
        'Domain Driven Design',
        'Linguagem ubíqua, Bounded Contexts, entidades, agregados e repositórios.',
        ('design_patterns', 'requirements'),
    ),
    _RoadmapSkill(
        'layered',
        'Arquitetura em camadas',
        'Separar apresentação, aplicação, domínio e infraestrutura; monólito modular.',
        ('mvc',),
    ),
    _RoadmapSkill(
        'hexagonal',
        'Arquitetura hexagonal e Clean Architecture',
        'Portas, adaptadores e regras de dependência voltadas ao domínio.',
        ('layered', 'solid'),
    ),
    _RoadmapSkill(
        'microservices',
        'Arquitetura de microsserviços',
        'Dividir um sistema em serviços independentes e implantáveis.',
        ('hexagonal', 'docker'),
    ),
    _RoadmapSkill(
        'event_driven',
        'Arquitetura orientada a eventos',
        'Produtores, consumidores e eventos para integrar serviços.',
        ('microservices',),
    ),
    _RoadmapSkill(
        'serverless',
        'Arquitetura serverless',
        'Funções sob demanda e serviços gerenciados na nuvem.',
        ('cloud',),
    ),
    _RoadmapSkill(
        'messaging',
        'Mensageria e filas',
        'Filas, tópicos e processamento assíncrono para reduzir carga e latência.',
        ('event_driven',),
    ),
    _RoadmapSkill(
        'scalability',
        'Escalabilidade e balanceamento de carga',
        'Escala vertical e horizontal, auto scaling, réplicas e sharding.',
        ('requirements', 'cloud'),
    ),
    _RoadmapSkill(
        'consistency',
        'Consistência de dados e Teorema CAP',
        'Tipos de consistência, ACID e BASE, idempotência e o Teorema CAP.',
        ('transactions',),
    ),
    _RoadmapSkill(
        'resilience',
        'Disponibilidade e resiliência',
        'Redundância, failover, degradação gradual e monitoramento.',
        ('scalability',),
    ),
    _RoadmapSkill(
        'system_design',
        'System Design',
        'Projetar sistemas distribuídos equilibrando escala, consistência e custo.',
        ('scalability', 'consistency', 'resilience'),
    ),
)

_ID_PREFIX = '01SHFRM'


def _roadmap_id(skill_index: int, item: int) -> str:
    return f'{_ID_PREFIX}{0:014d}{skill_index:03d}{item:02d}'


def build_roadmap_skills_seed(anchors: Mapping[str, str]) -> RoadmapSkillsSeed:
    """Build the roadmap; `anchors` maps foundation keys to existing Skill ids."""
    skill_ids = {
        roadmap_skill.key: _roadmap_id(index, 0)
        for index, roadmap_skill in enumerate(_ROADMAP_SKILLS, start=1)
    }
    if skill_ids.keys() & anchors.keys():
        raise ValueError('Roadmap keys must not shadow anchor keys')
    known_ids = {**anchors, **skill_ids}

    skills: list[Skill] = []
    foundations: list[SkillFoundation] = []
    contents: list[ReadySkillContent] = []
    for index, roadmap_skill in enumerate(_ROADMAP_SKILLS, start=1):
        skill = Skill(
            id=skill_ids[roadmap_skill.key],
            name=roadmap_skill.name,
            description=roadmap_skill.description,
        )
        skills.append(skill)
        foundations.extend(
            SkillFoundation(skill_id=skill.id, foundation_skill_id=known_ids[key])
            for key in roadmap_skill.foundations
        )
        contents.append(
            ReadySkillContentFaker.fake(
                skill=skill,
                id_for=lambda item, index=index: _roadmap_id(index, item),
            )
        )

    return RoadmapSkillsSeed(
        skills=tuple(skills),
        skill_foundations=tuple(foundations),
        competencies=tuple(content.competency for content in contents),
        concepts=tuple(content.concept for content in contents),
        materials=tuple(content.material for content in contents),
        activities=tuple(
            activity for content in contents for activity in content.activities
        ),
        curriculum_sequences=tuple(content.curriculum_sequence for content in contents),
    )

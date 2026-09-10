# Stack Tecnológica — Shifu

## Frontend

| Área | Tecnologia |
|---|---|
| Linguagem | TypeScript 7.0.2 |
| UI | React 19.2.8 |
| Framework | TanStack Start 1.168.50 |
| Roteamento | TanStack Router 1.170.32 |
| Runtime / Package Manager | Bun 1.4.2 |
| Componentes UI | shadcn/ui — CLI 4.21.0 |
| Estilização | Tailwind CSS 4.3.3 |
| Validação | Zod 4.5.4 |
| Server State / Cache | TanStack Query 5.102.8 |
| Formulários | TanStack Form 1.33.5 |
| Autenticação | Better Auth |
| Testes | Vitest 5.0.0 |
| Testes de Componentes | React Testing Library 16.3.3 |
| Testes E2E | Playwright 1.63.0 |
| Lint + Format | Biome 2.5.12 |
| Tipagem | TypeScript 7.0.2 / `tsc --noEmit` |
| Qualidade | SonarQube Community Build 26.9.0 — projeto `Shifu Web` |

## Frontend — Funcionalidades Específicas

| Área | Tecnologia |
|---|---|
| Grafo / Árvore de Habilidades | React Flow |
| Layout automático do grafo | ELK.js |
| Editor de código | A definir entre Monaco Editor e CodeMirror |
| Streaming do Mentor | Server-Sent Events — SSE |

## Backend

| Área | Tecnologia |
|---|---|
| Linguagem | Python 3.13 |
| Framework HTTP | FastAPI |
| Gerenciamento Python | uv |
| Validação / Schemas | Pydantic v2 |
| Banco de Dados | PostgreSQL |
| ORM | SQLAlchemy 2 |
| Migrações | Alembic |
| Driver PostgreSQL | psycopg 3 |
| Autenticação | Better Auth no TanStack Start |
| Autenticação BFF → API | JWT validado via JWKS |
| Autorização | FastAPI / regras do domínio |
| PLN Clássico | NLTK |
| ML / Representação Textual | scikit-learn |
| Busca por Linguagem Natural | TF-IDF |
| Similaridade Textual | TF-IDF + similaridade de cosseno |
| Classificação de Intenção | scikit-learn — Logistic Regression ou SVM |
| Processamento Assíncrono | Inngest |
| Linguagem das Atividades de Código | Python |
| Execução de Código | Sandbox isolada orquestrada pelo FastAPI |
| Testes | pytest |
| Testes das Rotas FastAPI | FastAPI `TestClient` |
| Testes de Infraestrutura | Testcontainers |
| Cobertura | pytest-cov |
| Lint + Format | Ruff |
| Tipagem | Pyright |
| Qualidade | SonarQube Community Build 26.9.0 — projeto `Shifu API` |
| Contrato da API | OpenAPI gerado pelo FastAPI |

## Arquitetura

```text
Browser
   ↓
TanStack Start / React
   │
   ├── Better Auth
   ├── TanStack Query
   ├── React Flow + ELK.js
   └── SSE
   │
   ↓
BFF TanStack Start
   │
   │ JWT
   ↓
FastAPI
├── Identity
├── Curriculum
├── Learning
├── Intelligence
│   └── PLN
│       ├── NLTK
│       └── scikit-learn
├── Gamification
│
├── PostgreSQL
├── Inngest
└── Code Execution
    ↓
Sandbox Python
````

## Organização do Monorepo

```text
shifu/
├── apps/
│   ├── web/
│   │   └── TanStack Start / React / TypeScript
│   │
│   └── api/
│       └── FastAPI / Python
│
├── docs/
│   ├── prds/
│   ├── specs/
│   └── architecture/
│
└── ...
```

## Qualidade

```text
Frontend
├── Biome
├── TypeScript / tsc
├── Vitest
├── React Testing Library
├── Playwright
└── SonarQube
    └── Shifu Web

Backend
├── Ruff
├── Pyright
├── pytest
├── TestClient
├── Testcontainers
├── pytest-cov
└── SonarQube
    └── Shifu API
```

Uma única instância do SonarQube pode hospedar os dois projetos:

```text
SonarQube
├── Shifu Web
└── Shifu API
```

## Processamento Assíncrono

O Inngest será utilizado para trabalhos que não precisam ser concluídos durante a requisição HTTP atual, como:

* envio de e-mails;
* tarefas periódicas;
* reindexação relacionada ao PLN;
* processamentos secundários;
* jobs demorados;
* efeitos assíncronos entre módulos.

Operações que exigem resposta imediata permanecem diretamente no FastAPI.

## Execução de Código

O FastAPI será responsável por orquestrar a execução de código Python, porém o código enviado pelo usuário será executado em uma sandbox isolada.

```text
React
   ↓
FastAPI
   ↓
Code Execution
   ↓
Sandbox
├── Python
├── timeout
├── CPU limitada
├── memória limitada
├── filesystem isolado
└── rede bloqueada
```

A aplicação distingue:

```text
Executar
→ executa o código
→ retorna stdout / stderr
→ não altera progresso

Enviar
→ executa testes oficiais
→ gera avaliação
→ atualiza progresso
→ pode gerar efeitos de Gamification
```


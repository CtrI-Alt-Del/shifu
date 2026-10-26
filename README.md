<div align="center">
  <h1>Assistente Virtual para Desenvolvimento de Habilidades: Shifu 🥋</h1>
</div>

## 🎯 Descrição do desafio

A GSW é uma empresa de tecnologia que desenvolve soluções corporativas e busca explorar o uso consciente de inteligência artificial aplicada à educação. O desafio consiste em desenvolver um assistente virtual que atue como mentor no desenvolvimento de habilidades, capaz de identificar o nível real de partida do aprendiz, montar uma jornada personalizada, entregar prática com correção e retorno, medir a evolução de forma comprovável e sustentar o engajamento ao longo do tempo. A solução não deve entregar respostas prontas, e sim guiar o usuário até o aprendizado. Duas restrições orientam toda a arquitetura: o consumo de IA precisa ser consciente, definindo explicitamente o que passa pelo modelo e o que é resolvido por lógica própria da aplicação, e o produto não pode deixar de ser útil quando a IA estiver indisponível. O caso funcional de validação do MVP é Lógica de Programação, com atividades práticas de código.

## 📖 Backlog do Produto

| RF | Rank | Prioridade | User story | Estimativa | Sprint |
|-----|------|------------|------------|------------|--------|
| 01 | 1 | Alta | Como usuário, quero criar e confirmar minha conta com nome, e-mail e senha, para que meus dados e experiências permaneçam associados a mim. | 5 | Sprint 1 · SHIFU-31 |
| 01 | 2 | Alta | Como usuário, quero entrar na aplicação e recuperar meu acesso caso esqueça a senha, para não perder minha jornada de aprendizagem. | 5 | Sprint 1 · SHIFU-32 |
| 03 | 3 | Alta | Como usuário, quero criar um Objetivo e adicionar Habilidades a ele, para organizar o que pretendo desenvolver. | 6 | Sprint 1 · SHIFU-34, SHIFU-35 |
| 03 | 4 | Alta | Como usuário, quero realizar um diagnóstico completo da Habilidade, para descobrir meu ponto de partida sem começar em conteúdo que já domino. | 8 | Sprint 1 · SHIFU-16 |
| 03 | 5 | Alta | Como usuário, quero acessar materiais de apoio e atividades na ordem definida do conteúdo, para estudar e praticar a Competência atual. | 6 | Sprints 1 e 2 · SHIFU-40, SHIFU-17 |
| 03 | 6 | Alta | Como usuário, quero enviar respostas de questões objetivas e de código e receber uma avaliação, para saber se minha solução está correta. | 21 | Sprint 1 · SHIFU-19, SHIFU-20, SHIFU-41 |
| 03 | 7 | Alta | Como usuário, quero acompanhar meu progresso e domínio por Competência, para perceber minha evolução real na Habilidade. | 5 | Sprint 1 · SHIFU-21 |
| 03 | 8 | Alta | Como usuário, quero receber a recomendação da próxima atividade na dificuldade adequada, para saber o que fazer em seguida sem escolher no escuro. | 5 | Sprint 1 · SHIFU-18 |
| 03 | 9 | Média | Como usuário, quero entender minha nota e o que mudou no meu progresso, para saber exatamente o que preciso melhorar. | – | Não associada · SHIFU-22 |
| 04 | 10 | Média | Como usuário, quero descrever livremente o que desejo aprender e responder perguntas objetivas, para receber uma proposta de Objetivo formada por Habilidades reais do produto. | 21 | Sprint 2 · SHIFU-43, SHIFU-44 |
| 04 | 11 | Média | Como usuário, quero conversar com um mentor que conheça meu contexto atual, para receber dicas progressivas sem receber a solução pronta. | 21 | Sprint 2 · SHIFU-45, SHIFU-46, SHIFU-47 |
| 05 | 12 | Média | Como usuário, quero receber XP e subir de nível conforme pratico, para me sentir reconhecido pelo meu esforço. | 8 | Sprint 2 · SHIFU-48 |
| 05 | 13 | Média | Como usuário, quero manter uma sequência de dias de prática, para sustentar minha constância. | 5 | Sprint 2 · SHIFU-49 |
| 05 | 14 | Baixa | Como usuário, quero desbloquear conquistas por marcos claros, para ter metas intermediárias visíveis. | 8 | Sprint 2 · SHIFU-50 |
| 03 | 15 | Baixa | Como usuário, quero consultar o histórico das minhas tentativas e o resumo final de uma Habilidade concluída, para revisar minha trajetória. | – | Não associada · SHIFU-53 |
| 04 | 16 | Baixa | Como usuário, quero saber quanto da minha cota mensal de IA ainda está disponível, para não ser surpreendido por um bloqueio temporário. | 8 | Sprint 2 · SHIFU-54 |
| 01 | 17 | Baixa | Como usuário, quero excluir minha conta e meus dados associados, para encerrar minha participação no produto. | 21 | Sprint 2 · SHIFU-33, SHIFU-116 |

**Legenda dos requisitos funcionais:** `01` Identity · `02` Curriculum · `03` Learning · `04` Intelligence · `05` Gamification

> A estimativa é a soma dos Story Points das histórias do Jira associadas a cada linha. A associação entre os requisitos e as histórias foi feita a partir dos [backlogs do projeto](documentation/sprints/backlogs-relatorio.md). Histórias concluídas sem sprint no Jira (SHIFU-37, 38, 39 e 42) e histórias sem estimativa não entram na soma.

---

## 🗓️ Cronograma e Sprints do projeto

| Sprint |    Período da Sprint    | Documentação | Status |
| :----: | :---------------------: | :----------: | :----: |
|   01   | 15/09/2026 – 27/09/2026 | [Relatório](documentation/sprints/sprint-1-report.md) · [Backlog](documentation/sprints/backlog-sprint-1.md) | Concluída |
|   02   | 05/10/2026 – 25/10/2026 | [Relatório](documentation/sprints/sprint-2-report.md) · [Backlog](documentation/sprints/backlog-sprint-2.md) | Concluída |
|   03   | A definir | A definir | Não iniciada |

## 🛠️ Tecnologias

| Área | Web (`apps/web`) | Servidor (`apps/server`) |
| --- | --- | --- |
| Linguagem | TypeScript 6 | Python 3.13 |
| Framework | TanStack Start e TanStack Router, com React 19 | FastAPI |
| Dados | TanStack Query e Axios | PostgreSQL, SQLAlchemy 2, Alembic e Redis |
| Interface | Tailwind CSS 4, shadcn/ui, React Flow e Monaco Editor | – |
| Autenticação | Better Auth, com BFF no TanStack Start | JWT validado por JWKS |
| Processamento assíncrono | – | Inngest, filas do Agno AgentOS e armazenamento S3 privado (MinIO local) |
| Linguagem natural | – | NLTK, scikit-learn, spaCy e embeddings E5 com pgvector |
| Testes | Vitest, React Testing Library e Playwright | pytest e Testcontainers |
| Qualidade | Biome, `tsc` e SonarQube | Ruff, Pyright e SonarQube |

O repositório é um workspace pnpm. O servidor usa uv. A infraestrutura local roda com Docker Compose. A arquitetura completa e as decisões em aberto estão em [`documentation/architecture.md`](documentation/architecture.md).

O desafio impõe restrições que orientam a arquitetura:

- **Uso consciente de IA** → o sistema decide explicitamente o que é resolvido por lógica própria e o que exige um modelo generativo, medindo e controlando o consumo.

- **Resiliência** → diagnóstico, trilha, prática, correção objetiva, progresso e gamificação continuam funcionando quando a IA está indisponível.

- **Processamento de Linguagem Natural** → vetorização, embeddings e similaridade semântica feitos pelo próprio time, e não apenas o consumo de uma API de terceiros.

- **Execução de código do usuário** → a prática de código roda no navegador, em WebContainers. A avaliação oficial lê o código enviado e aplica a rubrica do Currículo. O servidor nunca executa o código do usuário.

- **Avaliação qualitativa por IA** → critérios definidos previamente no conteúdo, com nota e explicação por critério, sem que a IA decida nota final, progresso ou conclusão.

- **Responsividade e acessibilidade** → os fluxos principais funcionam em desktop e mobile, são operáveis por teclado e não dependem apenas de cor.

## 📁 Estrutura do Repositório

O produto está organizado em módulos com responsabilidades bem separadas:

- **Identity**: conta, confirmação de e-mail, acesso, sessões, perfil e exclusão de conta
- **Curriculum**: Habilidades, Competências, materiais de apoio, sequência curricular, atividades e regras de avaliação
- **Learning**: Objetivos, diagnóstico, tentativas, avaliações, progresso, domínio, recomendação e conclusão
- **Intelligence**: Mentor contextual, Planejador de Objetivos e controle da cota de IA
- **Gamification**: XP, nível, sequência, conquistas, calendário de atividade e histórico de recompensas

Pastas do repositório:

- **`apps/web`**: aplicação web (TanStack Start e React)
- **`apps/server`**: API (FastAPI), com um pacote por módulo em `src/shifu`
- **`packages/email`**: modelos de e-mail transacional
- **`packages/studio`**: pacote de apoio com interface própria
- **`packages/iac`**: laboratório Terraform de armazenamento S3
- **`iac`**: Terraform da infraestrutura de staging na AWS
- **`design`**: arquivo de design no Pencil (`shifu.pen`) e referências visuais
- **`documentation`**: arquitetura, módulos, regras de engenharia, especificações e relatórios das sprints

## ▶️ Como executar o projeto

Requisitos: Node.js 24.20.0, pnpm, Python 3.13.5, uv e Docker com Docker Compose. Os comandos completos estão em [`documentation/tooling.md`](documentation/tooling.md).

1. Copie os arquivos de ambiente a partir dos exemplos:

   ```bash
   cp .env.example .env
   cp apps/web/.env.example apps/web/.env.local
   cp apps/server/.env.example apps/server/.env.local
   ```

2. Instale as dependências:

   ```bash
   corepack enable
   pnpm install
   cd apps/server && uv sync
   ```

3. Suba a infraestrutura local (PostgreSQL, Redis, Inngest, MinIO e Mailpit):

   ```bash
   docker compose up -d
   ```

4. Prepare o banco de dados em `apps/server`:

   ```bash
   uv run poe db:upgrade
   uv run poe db:seed
   ```

   O `db:seed` apaga os dados da aplicação e só roda em modo local.

5. Inicie o servidor em `apps/server`. Ele responde em `http://localhost:7777`:

   ```bash
   uv run poe dev
   ```

6. Inicie a aplicação web na raiz do repositório. Ela responde em `http://localhost:7000`:

   ```bash
   pnpm --filter web dev
   ```

## 🎥 Demonstração em Vídeo

- Link ainda não publicado

## 📚 Links Úteis

- [PRDs do produto](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/82804737/PRD+s)
- [Design System e Especificação de Telas](documentation/design.md)
- [Arquitetura](documentation/architecture.md)
- [Módulos do produto](documentation/modules.md)
- [Infraestrutura](documentation/infrastructure.md)
- [Ferramentas e comandos](documentation/tooling.md)
- [Relatórios e backlogs das sprints](documentation/sprints/)
- [DoR (Definition of Ready)](documentation/development/dor.md)
- [DoD (Definition of Done)](documentation/development/dod.md)
- [Estratégia de branches](documentation/development/branch-strategy.md)
- [Padrão de commit](documentation/development/commit-pattern.md)

## 👷🏻 Equipe

|                                    Foto                                    |          Nome           |    Função     |                                                                            Github                                                                            |                                                                                              Linkedin                                                                                               |
| :------------------------------------------------------------------------: | :---------------------: | :-----------: | :----------------------------------------------------------------------------------------------------------------------------------------------------------: | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
|       <img src="https://github.com/Tico1606.png?size=50" width="50">       |    Gabriel Oliveira     | Scrum Master  |       <a href="https://github.com/Tico1606"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white"></a>       |          <a href="https://www.linkedin.com/in/gabriel-oliveira-884ba5282/"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white"></a>           |
|  <img src="https://github.com/JoaoGabrielGarcia.png?size=50" width="50">   |  Joao Gabriel Oliveira  | Product Owner |  <a href="https://github.com/JoaoGabrielGarcia"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white"></a>   |  <a href="https://www.linkedin.com/in/jo%C3%A3o-gabriel-oliveira-garcia-b2563a22a/"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white"></a>  |
|      <img src="https://github.com/JohnPetros.png?size=50" width="50">      |   Joao Pedro Carvalho   |   Dev Team    |      <a href="https://github.com/JohnPetros"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white"></a>      | <a href="https://www.linkedin.com/in/jo%C3%A3o-pedro-carvalho-dos-santos-42a0ab222/"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white"></a> |
|        <img src="https://github.com/kaufon.png?size=50" width="50">        |  Kauan Fonseca do Vale  |   Dev Team    |        <a href="https://github.com/kaufon"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white"></a>        |            <a href="https://www.linkedin.com/in/kauan-fonseca-b62188300/"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white"></a>            |
|        <img src="https://github.com/0thigs.png?size=50" width="50">        |     Thiago Martins      |   Dev Team    |        <a href="https://github.com/0thigs"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white"></a>        |            <a href="https://www.linkedin.com/in/thiago-martins-fullstack/"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white"></a>             |

# Sprint 2 — Relatório de resultado

> **Período:** 05/10/2026 – 25/10/2026 (BRT). A sprint termina em 25/10 às 23:30.
> **Meta (síntese documental):** ampliar o ciclo de aprendizagem da Sprint 1 com planejamento assistido, Mentor contextual e controlável, prática de projetos web, gamificação e gestão segura da conta e dos dados, preservando a aprendizagem diante de falhas dos serviços auxiliares.

## Como ler este relatório

Os números vêm do Jira (quadro 331, `Sprint = 498`), consultado em 25/10/2026. A decisão de fechamento é do solicitante: **todos os 55 tickets são considerados prontos**. Esse é o mesmo critério usado no relatório da Sprint 1.

O estado real do Jira na consulta é diferente e está registrado em cada tabela. Ele mostra 27 tasks `Concluído`, 1 task em `Code Review` e as 27 histórias ainda em `Fazendo`. As histórias só mudam de estado depois do aceite, então o Jira ainda não reflete o fechamento.

## Resumo executivo

O incremento da Sprint 2 cobre cinco frentes: Planejador de Objetivos com IA, Mentor conversacional completo, Gamificação, conta e privacidade, e prática de projetos web. A infraestrutura de staging, o CD, a telemetria e a qualidade de código também entraram.

O compromisso foi de **27 User Stories e 197 SP**, mais 28 tasks sem pontos. Isso é cerca de 3,4 vezes os 58 SP da Sprint 1. No fechamento considerado, os 55 tickets e os 197 SP estão entregues.

Quase metade do trabalho caiu em duas pessoas. João Pedro Carvalho ficou com 97 SP em histórias e 10 tasks.

## Requisitos entregues

### Planejador de Objetivos com IA (21 SP)

- Entrevista em lotes de perguntas objetivas, com uma pergunta por etapa e respostas preservadas ao navegar (SHIFU-43).
- Proposta de Objetivo com título, descrição e Habilidades existentes, cada uma com justificativa. Grafo e Lista alternáveis (SHIFU-44).
- Edição de título e descrição, reinício do planejamento e criação atômica do Objetivo em Learning, sem duplicar em caso de reenvio (SHIFU-44).
- Classificação e recuperação de Habilidades com processamento de linguagem natural (SHIFU-89).

### Mentor conversacional (65 SP)

- Conversas privadas com busca por título, retomada com contexto e resumo automático de conversas longas (SHIFU-45).
- Consulta ao contexto autorizado do aprendiz: Objetivos, progresso, tentativas e Currículo. Dados de diagnóstico e de outras contas ficam fora (SHIFU-46).
- Limites pedagógicos: o Mentor dá dicas e não entrega a solução de uma Atividade ativa (SHIFU-47).
- Cancelar e repetir uma resposta sem perder a mensagem (SHIFU-55).
- Memórias pessoais, com lista, mapa, busca, edição, exclusão e confirmação de dificuldade recorrente (SHIFU-106).
- Anexos privados de até 10 MB e 5 arquivos por mensagem, com indicação da fonte usada na resposta (SHIFU-107).
- Cards de confirmação para adicionar ou remover Habilidades, sempre validados por Learning (SHIFU-108).
- Ditado por voz com revisão do texto antes do envio, sem guardar áudio no histórico (SHIFU-109).

### Gamificação (31 SP)

- XP por Atividade, proporcional à nota e sem repetição, e XP por marcos de diagnóstico, domínio e conclusão (SHIFU-48).
- Nível calculado por XP e sequência de dias de prática, com fuso horário do aprendiz (SHIFU-49).
- Catálogo fixo de conquistas, com aba de conquistas obtidas e bloqueadas (SHIFU-50).
- Resumo, calendário de atividade e histórico de XP (SHIFU-51).
- Celebrações de nível e conquista que aparecem uma única vez (SHIFU-115).

### Conta, privacidade e dados (32 SP)

- Edição de nome e fuso horário, e encerramento definitivo da conta com eliminação coordenada entre módulos (SHIFU-33).
- Troca de senha informando a senha atual, encerrando os demais acessos (SHIFU-52).
- Política de privacidade pública em `/privacy`, com canal de atendimento (SHIFU-113).
- Atendimento verificado de pedidos sobre dados pessoais (SHIFU-114).
- Eliminação também em logs e cópias de segurança, com prazo de até 30 dias (SHIFU-116).

### Prática de projetos web (29 SP)

- Página HTML/CSS/JavaScript editável no navegador, com prévia, terminal e avaliação por rubrica (SHIFU-110).
- Aplicação React com os mesmos recursos e criação de arquivos quando a questão permite (SHIFU-111).
- Projeto integrado React e Fastify, com painel HTTP para testar a API (SHIFU-112).

### Resiliência e consistência (21 SP)

- Aprendizagem preservada quando a IA ou a Gamificação falham, com recuperação da mesma tentativa e sem duplicar nota ou XP (SHIFU-23).
- Cota mensal compartilhada de IA, com aviso em 80% e bloqueio opcional em 100% (SHIFU-54).
- Consulta de Competências, materiais e Atividades com ajuda contextual do Mentor (SHIFU-17).
- Remoção consistente de Habilidade e Objetivo nas novas integrações (SHIFU-36).

### Plataforma e operação

- Infraestrutura básica e de staging com Terraform, com o laboratório S3 validado (SHIFU-78, SHIFU-83).
- CD de Terraform e das aplicações para staging (SHIFU-85).
- SonarCloud no CI do Web e da API, com cobertura e quality gate (SHIFU-87).
- Telemetria estruturada em JSON no Web/BFF e na API (SHIFU-94).

## User Stories comprometidas

Todas pertencem ao compromisso da Sprint 2. Os pontos são os do campo de estimativa do Jira.

| Chave | User Story | Épico | SP | Responsável | Jira na consulta |
| --- | --- | --- | ---: | --- | --- |
| [SHIFU-17](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-17) | Consultar competências, teoria e prática com navegação e contexto integrados | 03 — Modelagem de Habilidades e Competências | 3 | João Pedro Carvalho | Fazendo |
| [SHIFU-23](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-23) | Preservar aprendizagem e recuperar operações quando IA ou Gamification falharem | 13 — Governança e Resiliência de IA | 5 | João Gabriel | Fazendo |
| [SHIFU-33](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-33) | Gerenciar perfil, fuso horário e excluir definitivamente a conta | 01 — Identidade e Conta do Usuário | 13 | João Pedro Carvalho | Fazendo |
| [SHIFU-36](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-36) | Remover Habilidade ou Objetivo preservando consistência nas novas integrações | 10 — Objetivos e Gestão de Múltiplas Habilidades | 3 | João Gabriel | Fazendo |
| [SHIFU-43](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-43) | Conduzir entrevista em lotes de perguntas objetivas | 14 — Planejador de Objetivos com IA | 8 | Thigz | Fazendo |
| [SHIFU-44](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-44) | Gerar, revisar, reiniciar e confirmar a proposta de Objetivo | 14 — Planejador de Objetivos com IA | 13 | Thigz | Fazendo |
| [SHIFU-45](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-45) | Gerenciar conversas privadas e retomar seu contexto no Mentor | 15 — Mentor Conversacional Completo | 8 | João Pedro Carvalho | Fazendo |
| [SHIFU-46](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-46) | Consultar contexto autorizado do Shifu durante a conversa com o Mentor | 15 — Mentor Conversacional Completo | 8 | João Pedro Carvalho | Fazendo |
| [SHIFU-47](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-47) | Orientar com limites pedagógicos sem entregar a solução de Atividade ativa | 15 — Mentor Conversacional Completo | 5 | João Pedro Carvalho | Fazendo |
| [SHIFU-48](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-48) | Conceder XP por Atividades e marcos de aprendizagem | 16 — Gamificação | 8 | Kauan Fonseca | Fazendo |
| [SHIFU-49](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-49) | Calcular nível e sequência de dias de prática | 16 — Gamificação | 5 | Kauan Fonseca | Fazendo |
| [SHIFU-50](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-50) | Desbloquear conquistas do catálogo fixo | 16 — Gamificação | 8 | Kauan Fonseca | Fazendo |
| [SHIFU-51](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-51) | Exibir resumo de Gamificação, calendário de atividade e histórico de XP | 16 — Gamificação | 5 | Kauan Fonseca | Fazendo |
| [SHIFU-52](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-52) | Alterar senha e proteger os acessos existentes | 01 — Identidade e Conta do Usuário | 3 | João Pedro Carvalho | Fazendo |
| [SHIFU-54](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-54) | Controlar e acompanhar a cota mensal compartilhada de IA | 13 — Governança e Resiliência de IA | 8 | Thigz | Fazendo |
| [SHIFU-55](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-55) | Cancelar ou repetir uma resposta do Mentor sem perder a mensagem | 15 — Mentor Conversacional Completo | 5 | João Pedro Carvalho | Fazendo |
| [SHIFU-106](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-106) | Gerenciar memórias pessoais utilizadas pelo Mentor | 15 — Mentor Conversacional Completo | 13 | João Pedro Carvalho | Fazendo |
| [SHIFU-107](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-107) | Enviar anexos privados ao Mentor e compreender suas análises | 15 — Mentor Conversacional Completo | 13 | João Pedro Carvalho | Fazendo |
| [SHIFU-108](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-108) | Confirmar adição ou remoção de Habilidades propostas pelo Mentor | 15 — Mentor Conversacional Completo | 8 | João Pedro Carvalho | Fazendo |
| [SHIFU-109](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-109) | Ditar, revisar e enviar uma mensagem ao Mentor | 15 — Mentor Conversacional Completo | 5 | João Pedro Carvalho | Fazendo |
| [SHIFU-110](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-110) | Praticar e receber avaliação de uma página HTML/CSS/JavaScript | 05 — Atividades e Práticas | 8 | João Gabriel | Fazendo |
| [SHIFU-111](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-111) | Praticar e receber avaliação de uma aplicação React | 05 — Atividades e Práticas | 8 | João Gabriel | Fazendo |
| [SHIFU-112](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-112) | Praticar e receber avaliação de um projeto integrado React e Fastify | 05 — Atividades e Práticas | 13 | João Pedro Carvalho | Fazendo |
| [SHIFU-113](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-113) | Consultar a política de privacidade e encontrar o canal de atendimento | 01 — Identidade e Conta do Usuário | 3 | João Gabriel | Fazendo |
| [SHIFU-114](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-114) | Solicitar atendimento verificado sobre meus dados pessoais | 01 — Identidade e Conta do Usuário | 5 | João Gabriel | Fazendo |
| [SHIFU-115](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-115) | Receber celebrações de níveis e conquistas sem repetição | 16 — Gamificação | 5 | Kauan Fonseca | Fazendo |
| [SHIFU-116](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-116) | Ter meus dados eliminados também em logs e cópias de segurança | 01 — Identidade e Conta do Usuário | 8 | gabrielsoliveira1606 | Fazendo |

**Total comprometido:** 197 SP em 27 histórias. **Considerado entregue no fechamento:** 197 SP.

### Pontos por épico

| Épico | Histórias | SP |
| --- | ---: | ---: |
| 15 — Mentor Conversacional Completo | 8 | 65 |
| 01 — Identidade e Conta do Usuário | 5 | 32 |
| 16 — Gamificação | 5 | 31 |
| 05 — Atividades e Práticas | 3 | 29 |
| 14 — Planejador de Objetivos com IA | 2 | 21 |
| 13 — Governança e Resiliência de IA | 2 | 13 |
| 03 — Modelagem de Habilidades e Competências | 1 | 3 |
| 10 — Objetivos e Gestão de Múltiplas Habilidades | 1 | 3 |
| **Total** | **27** | **197** |

## Tasks realizadas

O Jira contém 28 tasks, sem pontos próprios. Elas compõem o trabalho das histórias e não somam SP adicionais.

| Chave | Task | Tipo | Responsável | Jira na consulta |
| --- | --- | --- | --- | --- |
| [SHIFU-78](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-78) | Criar IAC básico do projeto | Logical Task | gabrielsoliveira1606 | Concluído em 23/10 |
| [SHIFU-79](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-79) | Implementar processamento de conquistas e aba de Conquistas | Dev Task | Kauan Fonseca | Concluído em 10/10 |
| [SHIFU-80](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-80) | Implementar calendário de prática e cálculo de sequências | Dev Task | Kauan Fonseca | Concluído em 18/10 |
| [SHIFU-81](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-81) | Implementar persistência e aba de Histórico de XP | Dev Task | Kauan Fonseca | Concluído em 23/10 |
| [SHIFU-82](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-82) | Implementar visão geral de Gamificação e cálculo de níveis | Dev Task | Kauan Fonseca | Concluído em 22/10 |
| [SHIFU-83](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-83) | Provisionar infraestrutura de staging com Terraform e validar o laboratório S3 | Logical Task | gabrielsoliveira1606 | Concluído em 24/10 |
| [SHIFU-84](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-84) | Implementar concessão de XP e integração das recompensas no resultado da Atividade | Dev Task | Kauan Fonseca | Concluído em 24/10 |
| [SHIFU-85](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-85) | Implementar CD de Terraform e aplicações do Shifu para staging | Logical Task | gabrielsoliveira1606 | Concluído em 25/10 |
| [SHIFU-86](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-86) | Implementar questões de página HTML/CSS/JavaScript em Atividades de aprendizagem | Dev Task | João Gabriel | **Code Review** |
| [SHIFU-87](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-87) | Integrar SonarCloud ao CI do Web e da API com cobertura, quality gate e comentários nos PRs | Logical Task | gabrielsoliveira1606 | Concluído em 25/10 |
| [SHIFU-88](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-88) | Implementar questões React em Atividades de aprendizagem | Dev Task | João Gabriel | Concluído em 21/10 |
| [SHIFU-89](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-89) | Implementar classificação e recuperação de Habilidades com PLN | Dev Task | Thigz | Concluído em 24/10 |
| [SHIFU-90](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-90) | Implementar questões integradas React + Fastify em Atividades de aprendizagem | Dev Task | João Pedro Carvalho | Concluído em 25/10 |
| [SHIFU-91](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-91) | Implementar fluxo do Planejador de Objetivos no backend | Dev Task | Thigz | Concluído em 24/10 |
| [SHIFU-92](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-92) | Implementar interface da entrevista do Planejador de Objetivos | Dev Task | Thigz | Concluído em 24/10 |
| [SHIFU-93](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-93) | Implementar revisão da proposta e reinício do planejamento | Dev Task | Thigz | Concluído em 24/10 |
| [SHIFU-94](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-94) | Implementar telemetria estruturada em JSON no Web/BFF e na API | Logical Task | gabrielsoliveira1606 | Concluído em 24/10 |
| [SHIFU-95](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-95) | Integrar criação do Objetivo planejado com Learning | Dev Task | Thigz | Concluído em 24/10 |
| [SHIFU-96](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-96) | Implementar página pública de Política de privacidade e seus pontos de acesso | Dev Task | João Gabriel | Concluído em 21/10 |
| [SHIFU-97](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-97) | Implementar perfil e segurança em Minha conta | Dev Task | João Pedro Carvalho | Concluído em 25/10 |
| [SHIFU-98](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-98) | Implementar exclusão definitiva da conta e eliminação coordenada dos dados | Dev Task | João Pedro Carvalho | Concluído em 25/10 |
| [SHIFU-99](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-99) | Implementar gestão de conversas do Mentor | Dev Task | João Pedro Carvalho | Concluído em 09/10 |
| [SHIFU-100](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-100) | Implementar respostas contextuais e recuperação | Dev Task | João Pedro Carvalho | Concluído em 13/10 |
| [SHIFU-101](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-101) | Implementar memórias do aprendiz | Dev Task | João Pedro Carvalho | Concluído em 23/10 |
| [SHIFU-102](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-102) | Implementar resumo e continuidade da conversa | Dev Task | João Pedro Carvalho | Concluído em 20/10 |
| [SHIFU-103](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-103) | Implementar anexos e análise de arquivos | Dev Task | João Pedro Carvalho | Concluído em 18/10 |
| [SHIFU-104](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-104) | Implementar ações confirmadas do Mentor | Dev Task | João Pedro Carvalho | Concluído em 24/10 |
| [SHIFU-105](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-105) | Implementar ditado por áudio | Dev Task | João Pedro Carvalho | Concluído em 13/10 |

## Distribuição do trabalho

| Responsável | Histórias | SP em histórias | Tasks |
| --- | ---: | ---: | ---: |
| João Pedro Carvalho | 12 | 97 | 10 |
| João Gabriel | 6 | 32 | 3 |
| Kauan Fonseca | 5 | 31 | 5 |
| Thigz | 3 | 29 | 5 |
| gabrielsoliveira1606 | 1 | 8 | 5 |
| **Total** | **27** | **197** | **28** |

Seis itens mudaram de responsável desde o planejamento de 05/10, todos de João Gabriel para João Pedro Carvalho: as histórias SHIFU-33, SHIFU-52 e SHIFU-112, e as tasks SHIFU-90, SHIFU-97 e SHIFU-98.

## Métricas de fechamento

| Métrica | Resultado |
| --- | ---: |
| Tickets na Sprint | 55 |
| Tickets considerados prontos no fechamento (decisão do solicitante) | 55 de 55 (100%) |
| User Stories | 27 |
| Tasks | 28 |
| Story Points comprometidos | 197 SP |
| Story Points considerados entregues | 197 SP |
| Capacidade de referência (Sprint 1) | 58 SP |
| Compromisso sobre a referência | cerca de 3,4 vezes |
| Tickets em `Concluído` no Jira na consulta | 27 de 55 (49%) |
| Tickets em `Code Review` no Jira na consulta | 1 (SHIFU-86) |
| Tickets em `Fazendo` no Jira na consulta | 27 (todas as histórias) |
| Story Points em histórias `Concluído` no Jira na consulta | 0 de 197 SP |

## Ritmo de conclusão das tasks

As 27 tasks concluídas no Jira foram resolvidas em dez dias diferentes. O ritmo ficou concentrado no fim da sprint.

| Dia | Tasks resolvidas |
| --- | ---: |
| 09/10 e 10/10 | 2 |
| 13/10 | 2 |
| 18/10 | 2 |
| 20/10 a 23/10 | 7 |
| 24/10 | 9 |
| 25/10 | 5 |

Catorze das 27 tasks (52%) foram resolvidas nos dois últimos dias. As tasks SHIFU-90 e SHIFU-98 foram resolvidas às 23:32 e 23:33 de 25/10, poucos minutos depois do fim configurado da sprint (23:30).

## Gráfico Burndown

Não anexei o gráfico do Jira. Ele não está acessível por esta consulta. Para completar o relatório, exporte o burndown do quadro 331 e salve em `documentation/media/burndown-sprint-2.png`.

## Riscos e observações para o fechamento

- **Meta:** o campo de meta da sprint no Jira está vazio. A meta deste relatório é uma síntese documental e precisa de confirmação da equipe.
- **Estado das histórias:** as 27 histórias estão em `Fazendo` no Jira. Elas passam a `Concluído` quando o aceite for registrado.
- **SHIFU-86:** a task de questões HTML/CSS/JavaScript está em `Code Review`. Ela sustenta a história SHIFU-110. Este relatório a considera pronta por decisão do solicitante, mas a revisão ainda não aconteceu no Jira.
- **Aceite e evidências:** não há vídeo, ata de aceite nem evidência de validação integrada vinculada. Concluir uma task não comprova os critérios da história.
- **Capacidade:** o compromisso de 197 SP não tem capacidade aprovada registrada. Com o fechamento em 100%, os 197 SP viram a nova referência, mas essa conclusão precisa de aceite para valer como capacidade.
- **Concentração de risco:** João Pedro Carvalho concentra 49% dos pontos e 10 das 28 tasks. Isso merece atenção no planejamento da Sprint 3.
- **Pendências de conteúdo:** a política de privacidade (SHIFU-113) depende de decisões aprovadas sobre responsáveis, bases legais e fornecedores. O relatório não confirma que esse conteúdo foi aprovado.
- **Backlog fora da sprint:** SHIFU-22 e SHIFU-53 continuam sem estimativa e sem sprint.

## Fontes

- Jira, projeto Shifu, quadro 331: `project = SHIFU AND sprint = 498`, 55 issues, consultado em 25/10/2026. Estados de fechamento conforme decisão do solicitante.
- Descrições e critérios de aceitação das 27 histórias no Jira, consultados em 25/10/2026.
- [Backlog da Sprint 2](backlog-sprint-2.md), atualizado em 05/10/2026, usado para comparar o planejamento original.
- [Relatório da Sprint 1](sprint-1-report.md), usado como modelo.

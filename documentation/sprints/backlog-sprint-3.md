# Backlog da Sprint 3 — Shifu

**Estado: finalizada.** Atualizado em 22/11/2026 a partir do Jira e do [relatório local de resultado](sprint-3-report.md).

## Identificação

| Campo | Definição |
| --- | --- |
| Sprint | SHIFU Sprint 3 — ID 499, quadro 331 |
| Estado | Finalizada. O Jira ainda mostra a sprint como `active`; o encerramento no quadro não foi feito |
| Período | 05/11/2026 (16:00) a 22/11/2026 (23:30), America/Sao_Paulo |
| Capacidade estimada da equipe | Não registrada na fonte consultada |
| Referência histórica | Sprint 1: 58 SP em 11 histórias. Sprint 2: 197 SP em 27 histórias |
| Compromisso configurado | 3 User Stories, 8 SP. Só a SHIFU-54 tem estimativa |
| Tasks | 17; sem soma adicional de pontos |
| Itens vindos da Sprint 2 | 4: SHIFU-54, SHIFU-85, SHIFU-87 e SHIFU-98 |
| Previsão extra sem compromisso | Nenhum item classificado como extra. A SHIFU-132 foi criada em 12/11, depois do início, e provavelmente entrou durante a sprint. Não consegui confirmar |

## Meta e síntese do escopo

**Campo de meta no Jira: vazio.** A formulação abaixo é uma síntese documental dos tickets da sprint, a validar pela equipe. Não constitui aprovação retroativa:

> Ampliar o catálogo de Atividades com novos formatos de questão, fechar o ciclo da Habilidade com resumo de evolução e revisão, dar visibilidade ao uso de IA e reforçar a plataforma e a conta do usuário.

A sprint foi quase toda de tasks. Das 20 entregas, 17 são tasks sem pontos e só 3 são histórias. Por isso os 8 SP não medem o tamanho do trabalho e não permitem comparar com as Sprints 1 e 2.

## Encerramento e resultado

| Indicador | Resultado em 22/11/2026 |
| --- | --- |
| Histórias concluídas | 3 de 3 |
| SP concluídos | 8 de 8 |
| Tasks concluídas | 17 de 17 |
| Total de tickets | 20 de 20 concluídos |
| Meta atingida | A confirmar com a equipe; o campo de meta no Jira está vazio |
| Incremento demonstrável / evidências | A registrar após integração e aceite |
| Vídeo / ata de aceite | Não identificados nas fontes consultadas |
| Encerramento no Jira | Ainda não realizado |

## User Stories da Sprint

Os ranks abaixo são posições únicas da consulta atual do Product Backlog ordenada pelo campo Rank do Jira, excluindo SHIFU-2 (modelo de história). Não representam os ranks do planejamento das Sprints 1 e 2. Prioridades reproduzem o Jira (Medium → Média).

| Rank | Prioridade | Jira | User Story | Estimativa | Sprint | Estado |
| --- | --- | --- | --- | --- | --- | --- |
| 41 | Média | [SHIFU-54](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-54) | Como aprendiz, quero acompanhar o uso e renovação da minha cota compartilhada para usar Mentor e Planejador com previsibilidade. | 8 | 2 e 3 | Concluído |
| 42 | Média | [SHIFU-53](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-53) | Como usuário, quero concluir uma Habilidade e continuar consultando seu conteúdo, progresso e tentativas para reconhecer minha evolução sem perder o histórico de aprendizagem. | — | 3 | Concluído |
| 43 | Média | [SHIFU-22](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-22) | Como usuário, quero compreender por que recebi determinado resultado e o que devo revisar para aprender com cada tentativa, mesmo quando a IA não estiver disponível. | — | 3 | Concluído |

**Total: 3 histórias / 8 SP.** Entregas anteriores são base. Somente o incremento desta sprint é pontuado. Tasks não recebem pontos adicionais pelo mesmo trabalho. As SHIFU-22 e SHIFU-53 não têm estimativa, então os 8 SP subestimam o escopo.

## Valor de negócio

| História | Valor |
| --- | --- |
| [SHIFU-54](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-54) | Controle de consumo justo sem bloquear aprendizagem que não depende de IA. |
| [SHIFU-53](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-53) | Reconhecimento da evolução sem perder o histórico de aprendizagem. |
| [SHIFU-22](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-22) | Aprendizagem com cada tentativa, mesmo quando a IA está indisponível. |

## Frentes e integração

- Learning: novos formatos de questão (tradução, lacunas, associação, ordenação, Preparação Prática culinária e escolha por imagem), resumo de evolução e revisão da Habilidade concluída.
- Intelligence: cota compartilhada de IA, página Uso da IA e indicador de cota no cabeçalho.
- Gamification: lembrete de sequência por push no navegador, no horário escolhido.
- Identity: preferência de aparência em Minha conta, exclusão definitiva da conta e landing page pública.
- Plataforma e operação: CD de Terraform e das aplicações para staging, SonarCloud no CI e relatórios de S3, RDS e DynamoDB da atividade de armazenamento em nuvem.

Das 17 tasks, só 4 estão ligadas a uma história: SHIFU-85, SHIFU-98, SHIFU-118 e SHIFU-125. As outras 13 se ligam apenas a um épico ou a nenhum. Concluir uma task não conclui automaticamente a história relacionada.

## Definition of Ready

| Critério | Situação registrada | Evidência / pendência |
| --- | --- | --- |
| Título, descrição, ator e valor | Documentado | As 3 histórias descrevem resultado para aprendiz ou usuário. |
| Critérios de aceitação e regras | Documentado | Critérios e regras de negócio nos tickets. A SHIFU-54 tem CA-01 a CA-07. |
| Estimativa pela equipe | Parcial | Só a SHIFU-54 tem estimativa (8 SP). As SHIFU-22 e SHIFU-53 não têm. |
| Tasks vinculadas | Parcial | SHIFU-54 tem SHIFU-91, SHIFU-100 e SHIFU-118. SHIFU-53 tem SHIFU-125. SHIFU-22 não tem nenhuma. |
| Protótipo aprovado | Pendente | A checklist das SHIFU-22 e SHIFU-53 mostra o item desmarcado. |
| Design/documentação | Referências identificadas | PRDs de Learning e Intelligence citados nas histórias. |
| Compreensão validada com o time | Não comprovado | Ata não vinculada. |

O DoR não é declarado integralmente atendido.

## Tasks e responsáveis

| Jira | Tipo | Trabalho | Responsável | Estado | Épico / histórias relacionadas |
| --- | --- | --- | --- | --- | --- |
| [SHIFU-85](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-85) | Logical Task | Implementar CD de Terraform e aplicações do Shifu para staging | João Pedro Carvalho | Concluído | Sem épico. História [SHIFU-116](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-116) |
| [SHIFU-87](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-87) | Logical Task | Integrar SonarCloud ao CI do Web e da API com cobertura, quality gate e comentários nos PRs | João Pedro Carvalho | Concluído | Trabalho técnico transversal; sem US referenciada |
| [SHIFU-98](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-98) | Dev Task | Implementar exclusão definitiva da conta e eliminação coordenada dos dados | gabrielsoliveira1606 | Concluído | Épico 01. Histórias [SHIFU-33](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-33), [SHIFU-36](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-36), [SHIFU-114](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-114) e [SHIFU-116](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-116) |
| [SHIFU-118](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-118) | Dev Task | Implementar página Uso da IA e indicador de cota no cabeçalho | João Pedro Carvalho | Concluído | Épico 13. História [SHIFU-54](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-54) |
| [SHIFU-119](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-119) | Dev Task | Implementar preferência de aparência em Minha conta | Kauan Fonseca | Concluído | Épico 01; sem US referenciada |
| [SHIFU-121](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-121) | Dev Task | Implementar landing page pública do Shifu com foco em evolução visível | João Gabriel | Concluído | Épico 01; sem US referenciada |
| [SHIFU-122](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-122) | Dev Task | Implementar questões de tradução com digitação e ditado opcional | Kauan Fonseca | Concluído | Épico 05; sem US referenciada |
| [SHIFU-123](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-123) | Dev Task | Implementar questões de lacunas com banco de palavras e arrastar e soltar | Kauan Fonseca | Concluído | Épico 05; sem US referenciada |
| [SHIFU-124](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-124) | Dev Task | Implementar questões de associação de palavras e traduções | Kauan Fonseca | Concluído | Épico 05; sem US referenciada |
| [SHIFU-125](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-125) | Dev Task | Implementar resumo de evolução da Habilidade concluída e revisão sem alterar o resultado | Thigz | Concluído | Épico 07. História [SHIFU-53](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-53) |
| [SHIFU-126](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-126) | Logical Task | Entregar o relatório de S3 da atividade de armazenamento em nuvem, com anexos do Mentor | gabrielsoliveira1606 | Concluído | Sem épico; sem US referenciada |
| [SHIFU-127](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-127) | Logical Task | Entregar o relatório de RDS da atividade de armazenamento em nuvem, com banco espelhando o staging | gabrielsoliveira1606 | Concluído | Sem épico; sem US referenciada |
| [SHIFU-128](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-128) | Logical Task | Entregar o relatório de DynamoDB e a análise comparativa da atividade de armazenamento em nuvem, com eventos do Shifu | gabrielsoliveira1606 | Concluído | Sem épico; sem US referenciada |
| [SHIFU-129](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-129) | Dev Task | Implementar questões de ordenação de etapas | João Gabriel | Concluído | Épico 05; sem US referenciada |
| [SHIFU-130](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-130) | Dev Task | Implementar questões de Preparação Prática culinária | João Gabriel | Concluído | Épico 05; sem US referenciada |
| [SHIFU-131](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-131) | Dev Task | Implementar questões de escolha por imagem | Não atribuído | Concluído | Épico 05; sem US referenciada |
| [SHIFU-132](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-132) | Dev Task | Implementar lembrete de sequência por push no navegador com horário escolhido | João Pedro Carvalho | Concluído | Épico 16; sem US referenciada |

A distribuição acima reproduz o Jira. Duração inferior a 8 horas, datas de entrega e uma task em progresso por pessoa devem ser acompanhadas pelo time. Não estão declaradas como comprovadas por esta tabela. O burndown está no [relatório da sprint](sprint-3-report.md#gráfico-burndown).

### Épicos citados

| Épico | Nome no Jira |
| --- | --- |
| 01 | Identidade e Conta do Usuário |
| 05 | Atividades e Práticas |
| 07 | Acompanhamento de Progresso |
| 13 | Governança e Resiliência de IA |
| 16 | Gamificação: Engajamento, XP, Níveis, Sequência e Conquistas |

## Histórias que seguem no Product Backlog

Estas histórias vieram da Sprint 2 e **não estão na Sprint 3**. Na consulta de 22/11/2026, seguem em `Fazendo` no Jira, em uma sprint já fechada.

| Rank | Prioridade | Jira | User Story | Estimativa | Estado |
| --- | --- | --- | --- | --- | --- |
| 9 | Média | [SHIFU-33](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-33) | Gerenciar perfil, fuso horário e excluir definitivamente a conta | 13 | Fazendo |
| 12 | Média | [SHIFU-36](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-36) | Remover Habilidade ou Objetivo preservando consistência nas novas integrações | 3 | Fazendo |
| 38 | Média | [SHIFU-114](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-114) | Solicitar atendimento verificado sobre meus dados pessoais | 5 | Fazendo |
| 40 | Média | [SHIFU-116](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-116) | Ter meus dados eliminados também em logs e cópias de segurança | 8 | Fazendo |

**Total: 4 histórias / 29 SP.** A task SHIFU-98, concluída nesta sprint, está ligada às quatro.

A história SHIFU-133 (Acompanhar minha aprendizagem e meu engajamento no painel de Progresso) está `Concluído` no Jira e não pertence a nenhuma sprint.

## Estado e resultado

| Indicador | Situação em 22/11/2026 |
| --- | --- |
| Histórias concluídas | 3 de 3 |
| SP concluídos | 8 de 8 |
| Histórias em andamento | Nenhuma |
| Tasks em andamento | Nenhuma |
| Total de tickets | 20 de 20 concluídos |
| Meta atingida | A confirmar com a equipe |
| Incremento demonstrável / evidências | A registrar após integração e aceite |
| Encerramento no Jira | Ainda não realizado |

## Pendências de planejamento e acompanhamento

1. Registrar e confirmar a meta única da Sprint 3. O campo no Jira está vazio.
2. Encerrar a sprint no quadro do Jira.
3. Registrar a capacidade aprovada e estimar as SHIFU-22 e SHIFU-53, que não têm Story Points.
4. Revisar e mesclar os PRs abertos das SHIFU-98 ([PR 61](https://github.com/CtrI-Alt-Del/shifu/pull/61), rascunho), SHIFU-121 ([PR 65](https://github.com/CtrI-Alt-Del/shifu/pull/65)) e SHIFU-131 ([PR 64](https://github.com/CtrI-Alt-Del/shifu/pull/64)).
5. Decidir o destino das quatro histórias da Sprint 2 que seguem em `Fazendo` (SHIFU-33, SHIFU-36, SHIFU-114 e SHIFU-116).
6. Registrar aceite por história, evidências do incremento e resultado final, preservando o histórico das Sprints 1 e 2.

## Páginas relacionadas

- [Relatório da Sprint 3](sprint-3-report.md).
- [Backlog da Sprint 1](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/84017153).
- [Backlog da Sprint 2](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/101285889).
- [Relatório consolidado dos backlogs](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/85229570).

## Fontes e rastreabilidade

- Jira Shifu, quadro 331: sprint 499; consulta de estado em 22/11/2026.
- Descrições e critérios das histórias SHIFU-22, SHIFU-53 e SHIFU-54 no Jira.
- [Backlog do Produto — Shifu](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83623938), conteúdo 83623938; referência histórica de produto.
- [Backlog da Sprint 2](backlog-sprint-2.md), usado como modelo de formato.

O formato mantém Rank, Prioridade, User Story, Estimativa e Sprint, e explicita valor, capacidade, meta, extras e DoR. Jira é a fonte operacional. PRDs são a autoridade de produto. Este documento não altera tickets nem PRDs.

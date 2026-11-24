---
title: SHIFU-98 — encerramento e eliminação coordenada da conta
status: draft
revision: 3
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-98
scope:
  - Identity
  - Learning
  - Intelligence
  - Gamification
  - Communication
  - Web
last_updated_at: 2026-11-21
---

# Objective

Spec completa para concluir a SHIFU-98: permitir que uma pessoa encerre
definitivamente sua própria conta e coordenar o bloqueio de acesso e a
eliminação dos dados pessoais ativos de todos os módulos participantes.
Identity é dona do estado da conta e coordena o processo. Cada módulo elimina
os dados que possui.

O estado atual já apresenta a página /account/delete, mas o botão final fica
desabilitado e não existe encerramento ponta a ponta. O resultado solicitado
separa o encerramento imediato da eliminação, que pode permanecer pendente até
as confirmações dos participantes. A conta nunca é reativada e a interface não
declara eliminação concluída sem prova.

Modo complete devido aos riscos de autenticação, concorrência, persistência,
efeitos assíncronos, dados locais e dependências entre módulos. Esta revisão
permanece draft enquanto houver os bloqueios de autoridade e referência visual
registrados em Documentation Alignment.

# Scope

| Área / ator | Incluído | Excluído ou adiado |
| --- | --- | --- |
| Aprendiz autenticado, Identity | Encerramento da própria conta após senha atual e confirmação explícita; bloqueio imediato de sessões, links e novos efeitos. RP-09 parcial pelo limite de escopo do ticket; RP-10 completo para este fluxo. JN-09 e JN-10. | Edição de perfil/senha, cadastro e expiração automática de conta não confirmada. |
| Dados pessoais dos módulos | Eliminação coordenada em até 24 horas nos dados ativos, bases, caches, filas e efeitos pendentes de Identity, Learning, Intelligence, Gamification e Communication. Learning RP-29/RP-14/RP-23; Intelligence RP-11/RP-13/RP-14/RP-15/RP-16; Gamification RP-12; Communication RP-07/RP-08. | Alterar o ciclo geral de logs técnicos e backups, que continua sob a política vigente. |
| Navegadores com rascunhos | Invalidar e remover rascunhos locais na próxima comunicação com o Shifu, depois de confirmação de encerramento e validação online. Aplicar a exceção aprovada nas páginas Identity e Learning. | Considerar uma falha de conexão, token expirado ou falta de resposta como prova de remoção. |
| Reutilização de identidade | Permitir novo cadastro com o mesmo e-mail após remover a identidade técnica anterior, sem herdar dados ou associações. Identity RP-01/RP-09; JN-10. | Reativar a identidade anterior ou restaurar dados. |
| Operação e suporte | Retentativas duráveis e alerta operacional em falhas de eliminação, sem dados pessoais do aprendiz. | Serviço automatizado de exportação/atendimento de direitos, alteração de retenção geral, exclusão individual de Objetivo ou conversa e implementação da política pública. |
| Interface Web | Concluir página/modal existentes, estados de preparação, encerramento e eliminação pendente/concluída; desktop, mobile e teclado. | Alterar outros fluxos de conta fora dos ajustes de sessão e cache necessários à exclusão. |

O ticket também exclui a alteração do ciclo de backups e logs. O prazo de
eliminação em até 24 horas é aplicado aos dados ativos sob controle dos
módulos. A exceção para rascunhos em navegadores desconectados é específica:
eles só podem ser removidos na próxima comunicação do navegador após prova
online de encerramento.

## Design Contract

A página atual é /account/delete e monta o widget
apps/web/src/ui/identity/widgets/pages/account-deletion-page. Preservar o
contrato de destruição local do painel e reutilizar os tokens e primitivas
semânticas existentes. A Spec UI não autoriza inventar estados ou resultados
que o PRD não prevê.

| Superfície / rota | Estado / viewport | Página / board / componentes Penpot | CA / checagem visual | Desvios permitidos |
| --- | --- | --- | --- | --- |
| /account/delete | senha e confirmação, 1440×900 e 390×844 | Bloqueado: conexão Penpot MCP indisponível; os nomes atuais de página, board e componentes devem ser registrados após leitura pelo MCP. Os nós Pencil y2vJij e LbeWb são históricos e não são referência para esta Spec. | CA-10 / VM-04 | Nenhum desvio visual é aprovado até inspecionar o board. |
| /account/delete | confirmação, encerramento fechado e eliminação pendente/concluída, 1440×900 e 390×844 | Bloqueado pela mesma inspeção Penpot. Confirmar quais estados existem no design e reconciliar com o contrato de produto antes de marcar ready. | CA-10 / VM-04 | Nenhum desvio visual é aprovado até inspecionar o board. |

Preservar a página e o painel existentes. Reusar Dialog, Input, Checkbox,
Label, Button, Anchor e Icon, com tokens semânticos existentes. O design deve
separar estado transportado do estado de domínio. Não exportar nem criar pasta
de handoff local.

# Behavior Contract

| ID | RP/JN/fonte | Comportamento observável obrigatório |
| --- | --- | --- |
| RF-01 | Identity RP-09/RP-10, JN-09; SHIFU-98 | Somente uma conta ativa e autenticada pode encerrar a própria conta. Exigir senha atual correta e confirmação explícita; não aceitar accountId arbitrário do cliente. Cancelamento, senha incorreta, tentativa expirada ou falha anterior ao commit não encerra a conta. |
| RF-02 | Identity RP-09, JN-09 | Preparar a confirmação cria um intento curto, sem persistir senha ou consentimento. Após commit do encerramento, bloquear imediatamente sessões, links, emissão de sessão e novos efeitos pessoais. Não existe reativação. |
| RF-03 | Identity RP-09/RP-10, JN-09/JN-10 | A resposta separa conta encerrada de eliminação pendente ou concluída. Resposta perdida pode ser consultada por cookie de recuperação limitado; a consulta não devolve perfil, e-mail ou outro dado pessoal. |
| RF-04 | Identity RP-09; Learning RP-29; Intelligence RP-11/RP-13; Gamification RP-12; Communication RP-07/RP-08; política comum | Eliminar dados pessoais ativos de todos os participantes em até 24 horas após a confirmação válida. Cobrir bancos, caches, filas, mensagens e payloads ativos, anexos, rascunhos, memória, planejamento e dados de entrega que cada módulo controla. O Currículo compartilhado permanece. |
| RF-05 | Learning RP-14/RP-23; Intelligence RP-14/RP-15/RP-16; Gamification RP-12; Communication RP-08 | Evento tardio, job retomado, retry, callback ou concessão concorrente não recria dados nem executa efeito pessoal depois do encerramento. Reprocessar uma limpeza não duplica efeitos nem apaga dados de outra conta. |
| RF-06 | Identity RP-01/RP-09, JN-10 | Remover a identidade Better Auth, sessões, contas vinculadas e verificações associadas. Uma nova conta pode usar o mesmo e-mail com novo identificador, sem herdar progresso, objetivos, conversas, recompensas, propostas ou tokens anteriores. |
| RF-07 | Learning RP-09/RP-29; aditivo aprovado em Identity v6 e Learning v34 | Rascunho em IndexedDB/local storage não pode ser restaurado ou enviado sem validação online de uma capacidade associada ao navegador. Se a capacidade estiver revogada, apagar dados daquele accountId em todas as abas. Navegador offline preserva o rascunho local até comunicar-se com o Shifu; falha de rede e sessão expirada não são prova de encerramento. |
| RF-08 | Identity RP-09, JN-09; política comum | Falha de participante mantém a conta encerrada e a eliminação pendente, inicia retry durável e alerta a equipe. Nunca responder ou mostrar eliminação concluída sem confirmações válidas de todos os participantes e resolução de efeitos remotos incertos. |
| RF-09 | Identity RP-09/RP-10, JN-09; SHIFU-98 | O texto antes da confirmação explica caráter definitivo, bloqueio imediato, prazo de até 24 horas para dados sob controle do servidor e exceção do navegador desconectado. Consultar a política não confirma exclusão. Erros e estado pendente são compreensíveis e acessíveis por teclado. |
| RF-10 | Política comum, Jira SHIFU-98 | Não alterar retenção de logs e backups. Estado/data de encerramento e registros operacionais seguem apenas os limites da política vigente; não manter um tombstone permanente de usuário para compensar uma falha. |

| ID | RF | Dado | Quando | Então | Checks |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Sessão válida de conta ativa | Enviar senha incorreta, confirmação ausente ou cancelar | A conta, sessões, dados e filas não mudam; a interface não informa sucesso. Senha correta e confirmação explícita permitem iniciar o encerramento da própria conta. | CI-01 / CI-06 / VM-01 |
| CA-02 | RF-02/RF-03 | Intento de preparação válido | Confirmar e perder a resposta HTTP | A conta fica inacessível; a sessão antiga não autentica; o cookie de recuperação consulta o mesmo estado sem revelar PII. Repetir confirmação não cria segunda exclusão. | CI-01 / CI-06 / VM-02 |
| CA-03 | RF-02/RF-05 | Login, job ou efeito da mesma conta concorrente ao encerramento | Adquirir a barreira compartilhada/exclusiva | Se o fechamento faz commit, operação já admitida termina antes dele e a operação nova que aguardava falha fechada; nenhuma sessão ou efeito começa após o commit. Se um receipt in_flight/unknown impede o commit, a conta permanece ativa e não se afirma fechamento. | CI-02 / CI-03 |
| CA-04 | RF-04/RF-08 | Dados pessoais existentes em cada módulo, cache e fila | Coordenador inicia a eliminação | Cada participante apaga somente seus dados, registra confirmação idempotente e permite concluir dentro de 24 horas. Qualquer participante ausente ou sem confirmação mantém estado pendente. | CI-04 / CI-05 |
| CA-05 | RF-05/RF-08 | Evento antigo, retry duplicado ou worker retomado após o fechamento | Processar ou reprocessar | Nenhum dado/efeito pessoal é recriado. Resposta repetida de módulo com o mesmo erasureId é aceita; resposta incompatível é rejeitada e alertada. | CI-03 / CI-04 |
| CA-06 | RF-06 | Conta encerrada com e-mail e sessões Better Auth | Criar conta nova com o mesmo e-mail | Nova identidade tem novo accountId e não consulta dados, sessões, rascunhos ou associações da conta anterior. | CI-01 / CI-06 |
| CA-07 | RF-08 | Uma limpeza, provedor ou alerta falha; ou seu resultado é desconhecido após crash | Reexecutar o workflow | A conta permanece encerrada e pending; o retry não duplica efeitos externos; incidente gera alerta seguro. Resultado remoto desconhecido impede conclusão até reconciliação. | CI-04 / CI-05 |
| CA-08 | RF-07 | Rascunho local com capacidade ativa, revogada ou sem capacidade legada | Validar online, ficar offline, reconectar ou expirar sessão | Capacidade ativa não substitui sessão e autorização válidas. Revogada remove os dados locais. Falha de rede/401 genérico não remove nem restaura rascunho. Rascunho legado só é associado após login válido; impossibilidade de provar remoção mantém a eliminação pendente. | CI-07 / CI-08 / VM-03 |
| CA-09 | RF-03/RF-09 | Encerramento pendente e concluído | Atualizar a página, trocar de aba, fechar modal ou usar teclado | Estado persistido permanece consistente; senha/consentimento desaparecem ao fechar; foco é gerenciado; não há sucesso fictício, overflow horizontal ou ação destrutiva por consultar a política. | CI-08 / VM-01 / VM-02 |
| CA-10 | RF-09 | Estados de senha, confirmação, falha e eliminação pendente | Usar desktop/mobile e navegação por teclado | Controles têm rótulos e estados acessíveis, foco previsível e conteúdo responsivo. Aparência corresponde ao board Penpot atual, após inspeção. | CI-08 / VM-01 / VM-04 |
| CA-11 | RF-04/RF-08 | Incidente de eliminação que exige alerta | Gerar o alerta operacional | Destino é shifu.ctrlaltdel@gmail.com, conforme canal da política. Mensagem contém apenas erasureId opaco, módulo, código de falha e datas; não contém accountId, nome, e-mail, conteúdo, token ou payload do aprendiz. | CI-05 |

# Technical Contract

## Architecture Mapping

Owner: Identity coordena encerramento e estado de eliminação. Learning,
Intelligence, Gamification e Communication permanecem donos de seus próprios
dados e regras. Shared oferece apenas a barreira técnica de atividade e a
composição não injeta regras de negócio nos módulos.

Rules aplicáveis: documentation/rules.md; python-conventions,
typescript-conventions, core-layer, database-layer, provider-layer,
rest-layer, server-app-layer, messaging-layer, use-case-testing,
controllers-testing, jobs-testing, ui-layer, web-app-routing e
widget-testing. Revisar o Rule Pack novamente quando a implementação ampliar
seus limites.

| Ação | Limite | Elemento / caminho | Resultado contratual |
| --- | --- | --- | --- |
| Create | Shared Core | apps/server/src/shifu/shared/core/interfaces/account_activity_provider.py | Porta neutra para entrar na atividade de uma conta; não conhece módulos consumidores nem SQLAlchemy. |
| Create/Modify | Shared Database | apps/server/src/shifu/shared/database/sqlalchemy/account_activity_scope.py; apps/server/src/shifu/shared/database/sqlalchemy/session.py | Infraestrutura neutra da barreira PostgreSQL por advisory lock de sessão, modos shared/exclusive e conexão física pinada na primária. Timeout falha sem efeito; não reconectar silenciosamente dentro de escopo inválido. |
| Modify | Identity Core | apps/server/src/shifu/identity/core/domain/entities/account.py; apps/server/src/shifu/identity/core/interfaces/identity_database.py; apps/server/src/shifu/identity/core/interfaces/accounts_repository.py | Fechamento definitivo, incremento de access_version e leitura/revalidação sob a barreira exclusiva; APIs públicas de Core recebem identidade autenticada, nunca accountId fornecido pelo navegador. |
| Create | Identity Core | apps/server/src/shifu/identity/core/domain/structures/account_erasure.py; apps/server/src/shifu/identity/core/interfaces/account_erasure_repository.py; apps/server/src/shifu/identity/core/use_cases/delete_account_use_case.py; apps/server/src/shifu/identity/core/use_cases/get_account_erasure_status_use_case.py | Resultado separado de fechamento e eliminação, estado de participantes, vencimento e recuperação mínima sem PII. `erasureId` é também o identificador do fechamento; não existe `closureId` distinto. |
| Create | Identity Provider | apps/server/src/shifu/identity/providers/account_activity/sqlalchemy_account_activity_provider.py | Identity decide elegibilidade e titularidade. Shared fornece apenas o lock/conexão; o provider não transfere regras de módulo para Shared. |
| Modify/Create | Identity persistence | apps/server/src/shifu/identity/database/sqlalchemy/identity_database.py; apps/server/src/shifu/identity/database/sqlalchemy/models/account_erasure_model.py; apps/server/src/shifu/identity/database/sqlalchemy/repositories/account_erasure_repository.py; apps/server/src/shifu/identity/database/sqlalchemy/models/account_browser_capability_model.py; apps/server/src/shifu/identity/database/sqlalchemy/repositories/account_browser_capabilities_repository.py | Transação de fechamento, tabelas de coordenação/capacidades e índices idempotentes. Não manter mapeamento pessoal depois de concluída a eliminação. |
| Create/Modify | Identity REST e wiring | apps/server/src/shifu/identity/rest/controllers/delete_account_controller.py; apps/server/src/shifu/identity/rest/controllers/get_account_erasure_status_controller.py; apps/server/src/shifu/identity/rest/controllers/get_account_erasure_target_controller.py; apps/server/src/shifu/identity/rest/controllers/account_activity_admission_controller.py; apps/server/src/shifu/identity/rest/controllers/issue_browser_data_capability_controller.py; apps/server/src/shifu/identity/rest/controllers/validate_browser_data_capability_controller.py; apps/server/src/shifu/identity/rest/router.py | Endpoints tipados do contrato abaixo, autenticação/serviço adequada e registro do router. Nenhum controller possui regra de eliminação de outro módulo. |
| Create/Modify | Identity jobs e composição | apps/server/src/shifu/identity/messaging/inngest/identity_inngest_messaging.py; apps/server/src/shifu/identity/messaging/inngest/jobs/coordinate_account_erasure_job.py; apps/server/src/shifu/identity/messaging/inngest/jobs/sweep_account_erasure_job.py; apps/server/src/shifu/identity/messaging/inngest/jobs/close_bff_identity_on_account_erasure_job.py; apps/server/src/shifu/identity/core/use_cases/close_bff_identity_for_account_erasure_use_case.py; apps/server/src/shifu/identity/providers/account_erasure/http_account_erasure_bff_provider.py; apps/server/src/shifu/composition/account_erasure_workflow.py; apps/server/src/shifu/shared/constants/environment.py; iac/staging/compute.tf | Fanout, retry durável do participante BFF, coleta de acknowledgements e reconciliação. Evento novo transporta só erasureId opaco; destino BFF usa SHIFU_BFF_BASE_URL e credencial compartilhada. |
| Modify | Learning | apps/server/src/shifu/learning/core/interfaces/learning_database.py; apps/server/src/shifu/learning/messaging/inngest/learning_inngest_messaging.py; apps/server/src/shifu/learning/messaging/inngest/jobs/purge_learning_data_on_account_erasure_job.py; apps/web/src/core/learning/react-question-draft/react-question-draft-store.ts; apps/web/src/provision/learning/indexed-db-react-question-draft-store.ts | Eliminar objetivos, habilidades, tentativas, avaliações, progresso, recomendações e rascunhos do servidor; invalidar rascunhos do navegador e impedir replay. O Currículo compartilhado não é apagado. |
| Modify | Intelligence | apps/server/src/shifu/intelligence/messaging/inngest/intelligence_inngest_messaging.py; apps/server/src/shifu/intelligence/messaging/inngest/jobs/purge_mentor_summaries_on_account_deleted_job.py; apps/server/src/shifu/intelligence/messaging/inngest/jobs/purge_mentor_attachments_on_account_deleted_job.py; apps/server/src/shifu/intelligence/messaging/inngest/jobs/purge_mentor_action_proposals_on_account_deleted_job.py; apps/server/src/shifu/intelligence/messaging/inngest/jobs/purge_learner_memories_on_account_deleted_job.py; apps/server/src/shifu/intelligence/messaging/inngest/jobs/purge_ai_quota_on_account_deleted_job.py; apps/server/src/shifu/intelligence/providers/planning/redis/redis_planning_sessions_repository.py; apps/web/src/provision/intelligence/local-storage-ai-quota-warning-dismissal-store.ts | Limpeza por participante cobre anexos, sumarizações, memórias, ações/propostas, sessões Redis, quotas, identificadores e resultados pendentes. Remover atraso atual que posterga a primeira tentativa de anexos por 24 horas. |
| Modify | Gamification | apps/server/src/shifu/gamification/core/use_cases/delete_gamification_profile_use_case.py; apps/server/src/shifu/gamification/messaging/inngest/jobs/purge_profile_on_account_deleted_job.py; apps/server/src/shifu/gamification/messaging/inngest/jobs/create_profile_on_account_activated_job.py | Remover todos os registros pelo accountId mesmo quando não existe perfil-raiz; criação/ativação tardia verifica estado ativo e não recria o perfil. |
| Modify | Communication | apps/server/src/shifu/communication/core/use_cases/queue_communication_use_case.py; apps/server/src/shifu/communication/core/use_cases/cancel_communication_use_case.py; apps/server/src/shifu/communication/messaging/inngest/jobs/cancel_communication_job.py; apps/server/src/shifu/communication/messaging/inngest/jobs/deliver_communication_job.py; apps/server/src/shifu/communication/messaging/inngest/communication_inngest_messaging.py; apps/server/src/shifu/composition/password_recovery_workflow.py; apps/server/src/shifu/composition/registration_confirmation_workflow.py | Admitir filas sob a barreira da conta, cancelar entrega, retries e destinatários pendentes; validar atividade no momento da entrega; apagar payloads e tokens pessoais que cada fila possui. |
| Modify | Web UI e sessão | apps/web/src/routes/account/delete/index.tsx; apps/web/src/ui/identity/widgets/pages/account-deletion-page/deletion-panel/index.tsx; apps/web/src/ui/identity/widgets/pages/account-deletion-page/deletion-panel/use-deletion-panel.ts; apps/web/src/ui/identity/widgets/pages/account-deletion-page/deletion-panel/use-delete-account-action.ts; apps/web/src/ui/shared/contexts/auth-context/types/auth-context-value.ts; apps/web/src/ui/shared/contexts/auth-context/use-auth-context-provider.ts; apps/web/src/provision/auth/cookie-session-auth-provider.ts | Exibir preparação, validação, encerrado e pendente/concluído; fechar sessão/cache e navegar para estado público; fail-closed quando a identidade não pode ser confirmada. |
| Modify | Web API/BFF | apps/web/src/routes/api/auth/$.ts; apps/web/src/routes/api/auth/account/deletion/index.ts; apps/web/src/routes/api/auth/account/deletion/prepare.ts; apps/web/src/routes/api/identity/browser-data-capabilities/index.ts; apps/web/src/routes/api/identity/browser-data-validations/index.ts; apps/web/src/provision/auth/better-auth/better-auth-provider.ts; apps/web/src/provision/auth/account-activity-scope.ts | Implementar BFF, recuperação, validação local e participação do CRUD Better Auth na conexão pinada da barreira. Respeitar origem, cookie e resposta sem cache; não ativar delete-user nativo. Gerar routeTree.gen.ts apenas pelo comando documentado. |
| Modify | Web local data | apps/web/src/core/learning/react-question-draft/react-question-draft-store.ts; apps/web/src/provision/learning/indexed-db-react-question-draft-store.ts; apps/web/src/provision/intelligence/local-storage-ai-quota-warning-dismissal-store.ts | Invalidar atomicamente dados por conta, armazenar capacidade apenas localmente, respeitar marcador de revogação em leituras/escritas/limpeza, notificar abas e limpar query/memória. |
| Modify | Testes permitidos | arquivos definidos em Verification Contract | Provar via use cases, controllers, jobs, route/registered handler e widget/consumidor. Não criar teste direto de repository, provider, migration, REST service ou action hook fora dos limites autorizados pelo Rule Pack. |
| Generate | Banco | apps/server/migrations/versions/<revisão Alembic gerada e revisada> | Criar após revisar todos os heads atuais com autogenerate. Não reservar filename ou revision id antes da geração. Backfill e índices devem ser compatíveis com dados existentes. |

### Expected file tree

Os caminhos abaixo são os limites esperados do candidato; [N] significa novo,
[M] significa alteração e [G] significa saída gerada. A migration e a route
tree só são nomeadas pelo gerador instalado.

    apps/server/src/shifu/shared/core/interfaces/account_activity_provider.py [N]
    apps/server/src/shifu/shared/database/sqlalchemy/account_activity_scope.py [N]
    apps/server/src/shifu/shared/database/sqlalchemy/session.py [M]
    apps/server/src/shifu/identity/providers/account_activity/sqlalchemy_account_activity_provider.py [N]
    apps/server/src/shifu/composition/account_erasure_workflow.py [N]
    apps/server/src/shifu/identity/core/domain/entities/account.py [M]
    apps/server/src/shifu/identity/core/domain/structures/account_erasure.py [N]
    apps/server/src/shifu/identity/core/interfaces/identity_database.py [M]
    apps/server/src/shifu/identity/core/interfaces/account_erasure_repository.py [N]
    apps/server/src/shifu/identity/core/use_cases/delete_account_use_case.py [N]
    apps/server/src/shifu/identity/core/use_cases/get_account_erasure_status_use_case.py [N]
    apps/server/src/shifu/identity/database/sqlalchemy/identity_database.py [M]
    apps/server/src/shifu/identity/database/sqlalchemy/models/account_erasure_model.py [N]
    apps/server/src/shifu/identity/database/sqlalchemy/repositories/account_erasure_repository.py [N]
    apps/server/src/shifu/identity/database/sqlalchemy/models/account_browser_capability_model.py [N]
    apps/server/src/shifu/identity/database/sqlalchemy/repositories/account_browser_capabilities_repository.py [N]
    apps/server/src/shifu/identity/rest/controllers/delete_account_controller.py [N]
    apps/server/src/shifu/identity/rest/controllers/get_account_erasure_status_controller.py [N]
    apps/server/src/shifu/identity/rest/controllers/get_account_erasure_target_controller.py [N]
    apps/server/src/shifu/identity/rest/controllers/account_activity_admission_controller.py [N]
    apps/server/src/shifu/identity/rest/controllers/issue_browser_data_capability_controller.py [N]
    apps/server/src/shifu/identity/rest/controllers/validate_browser_data_capability_controller.py [N]
    apps/server/src/shifu/identity/rest/router.py [M]
    apps/server/src/shifu/identity/messaging/inngest/identity_inngest_messaging.py [M]
    apps/server/src/shifu/identity/messaging/inngest/jobs/coordinate_account_erasure_job.py [N]
    apps/server/src/shifu/identity/messaging/inngest/jobs/sweep_account_erasure_job.py [N]
    apps/server/migrations/versions/ [G: revisão Alembic, nome atribuído pelo gerador]
    apps/server/rest-client/identity/identity.rest [M]
    apps/server/src/shifu/learning/core/interfaces/learning_database.py [M]
    apps/server/src/shifu/learning/messaging/inngest/learning_inngest_messaging.py [M]
    apps/server/src/shifu/learning/messaging/inngest/jobs/purge_learning_data_on_account_erasure_job.py [N]
    apps/server/src/shifu/intelligence/messaging/inngest/intelligence_inngest_messaging.py [M]
    apps/server/src/shifu/intelligence/messaging/inngest/jobs/ [M: purges existentes de summaries, attachments, proposals, memories e quota]
    apps/server/src/shifu/intelligence/providers/planning/redis/redis_planning_sessions_repository.py [M]
    apps/server/src/shifu/gamification/core/use_cases/delete_gamification_profile_use_case.py [M]
    apps/server/src/shifu/gamification/messaging/inngest/jobs/purge_profile_on_account_deleted_job.py [M]
    apps/server/src/shifu/gamification/messaging/inngest/jobs/create_profile_on_account_activated_job.py [M]
    apps/server/src/shifu/communication/core/use_cases/cancel_communication_use_case.py [M]
    apps/server/src/shifu/communication/messaging/inngest/jobs/cancel_communication_job.py [M]
    apps/server/src/shifu/communication/messaging/inngest/jobs/deliver_communication_job.py [M]
    apps/server/src/shifu/communication/messaging/inngest/communication_inngest_messaging.py [M]
    apps/web/src/routes/api/auth/account/deletion/ [N: prepare e index]
    apps/web/src/routes/api/identity/browser-data-capabilities/index.ts [N]
    apps/web/src/routes/api/identity/browser-data-validations/index.ts [N]
    apps/web/src/routeTree.gen.ts [G]
    apps/web/src/ui/identity/widgets/pages/account-deletion-page/ [M: painel e action hook]
    apps/web/src/ui/shared/contexts/auth-context/ [M: contrato de auth e estado de sessão]
    apps/web/src/provision/auth/ [M: sessão/cookie Better Auth fail-closed]
    apps/web/src/provision/auth/account-activity-scope.ts [N]
    apps/web/src/core/learning/react-question-draft/react-question-draft-store.ts [M]
    apps/web/src/provision/learning/indexed-db-react-question-draft-store.ts [M]
    apps/web/src/provision/intelligence/local-storage-ai-quota-warning-dismissal-store.ts [M]
    apps/web/tests/identity/account-deletion-auth-api.test.ts [N]
    apps/server/tests/identity/core/use_cases/test_delete_account_use_case.py [N]
    apps/server/tests/identity/server/controllers/test_delete_account_controller.py [N]
    apps/server/tests/messaging/inngest/jobs/identity/test_coordinate_account_erasure_job.py [N]
    apps/server/tests/messaging/inngest/jobs/identity/test_sweep_account_erasure_job.py [N]
    apps/server/tests/messaging/inngest/jobs/learning/test_purge_learning_data_on_account_erasure_job.py [N]

Os arquivos UI históricos em
documentation/features/identity/account-deletion-ui/ permanecem inalterados.
Não criar evaluation.md até o início da implementação.

### Declarações públicas esperadas

Shared Core expõe somente o contrato técnico abaixo; implementação usa
PostgreSQL fora de Core:

    class AccountActivityProvider(Protocol):
        @contextmanager
        def activity(
            self,
            account_id: str,
            *,
            actor: AuthenticatedUser | None = None,
        ) -> Iterator[None]: ...

        @asynccontextmanager
        async def async_activity(
            self,
            account_id: str,
            *,
            actor: AuthenticatedUser | None = None,
        ) -> AsyncIterator[None]: ...

Identity Core precisa expor entrada de fechamento e resultado tipado:

    @dataclass(frozen=True)
    class DeleteAccountInput:
        account_id: str
        erasure_id: UUID
        current_password: str
        confirmed: bool

    class IdentityDatabase(Protocol):
        @contextmanager
        def account_closure_transaction(
            self,
            account_id: str,
        ) -> Iterator[IdentityDatabaseRepositories]: ...

    @dataclass(frozen=True)
    class AccountErasureResult:
        state: Literal["closed"]
        closed_at: datetime
        erasure: Literal["pending", "completed"]

O repositório da coordenação mantém um AccountErasure por fechamento, com
erasureId UUID, accountId operacional enquanto houver limpeza, closedAt, dueAt,
status e um registro único por participante. AccountId não pode sobreviver à
eliminação completa; resultado, código de erro e alertas não guardam nome,
email, token ou conteúdo. Índice único de participante por erasureId torna
acknowledgement idempotente. Repetir o mesmo estado não altera o resultado;
resposta incompatível falha e alerta.

A leitura do alvo pelo erasureId é limitada a serviços autenticados e retorna
somente accountId e erasureId durante o estado pending. A resposta fica apenas
na memória do handler da operação e não pode ser emitida como evento, saída de
step durável, log ou telemetria. O handler de participante a solicita novamente
em cada tentativa; não grava esse resultado no histórico de execução.

No Web, schemas Zod equivalentes aos seguintes shapes são usados nos limites:

    PrepareDeletionResponse = { state: "prepared" }
    ConfirmDeletionRequest = { currentPassword: string, confirmed: true }
    DeletionStatusResponse = {
      state: "closed",
      closedAt: ISO-8601 string,
      erasure: "pending" | "completed"
    }
    BrowserCapabilityResponse = { capability: string }
    BrowserCapabilityStatus = { state: "active" | "revoked" }

Não retornar accountId, email ou mensagem de erro interna ao navegador. A
capacidade de browser é segredo bearer: armazenar somente hash no servidor,
nunca em URL, evento, log ou telemetria.

### REST e eventos

| Método / caminho | Entrada e autenticação | Resposta e falhas |
| --- | --- | --- |
| POST /api/auth/account/deletion/prepare | Sessão ativa própria, origem válida; corpo vazio. | 201 com state prepared. BFF emite cookie assinado HttpOnly, Secure, SameSite=Strict por 24h com erasureId aleatório, vínculo opaco ao ator e validade inicial de confirmação de 15 min. O BFF usa a validade curta somente para o primeiro fechamento; repetição após commit usa o mesmo erasureId e a validade longa só consulta status. Não guarda senha/consentimento. |
| POST /api/auth/account/deletion | Sessão própria, origem válida, cookie de preparação válido; corpo com currentPassword e confirmed=true. Não aceita accountId nem erasureId do navegador. | 202 com AccountErasureResult. BFF vincula o cookie à sessão atual e encaminha seu erasureId assinado. Senha/estado/intent inválidos não fecham conta; indisponibilidade anterior ao commit retorna erro recuperável e sem efeitos. Após commit, fechamento está feito mesmo que a limpeza fique pending. |
| POST /identity/account-deletions | BFF encaminha bearer token da sessão, erasure_id assinado pelo BFF, currentPassword e confirmed=true. Actor vem do token validado; não aceita accountId. | 202 com AccountErasureResult. Identity vincula erasureId ao ator; repetição idempotente do mesmo ator retorna o mesmo estado e outro ator é recusado. Identity valida senha e estado sob a barreira exclusiva, grava DELETED/access_version/erasure/outbox no commit e nunca persiste senha. |
| GET /api/auth/account/deletion | Cookie de recuperação válido; não exige sessão encerrada. | 200 com estado mínimo e sem PII; cookie ausente/inválido recebe resposta indistinguível sem revelar existência de conta. Cache-Control: no-store. |
| GET /identity/internal/account-erasures/{erasure_id}/status | Credencial de serviço; chamado pelo BFF após validar cookie de recuperação. | 200 com state, closed_at e erasure pending/completed; nenhuma PII. Cache-Control: no-store. Ausente e desconhecido retornam resultado indistinguível. |
| GET /identity/internal/account-erasures/{erasure_id}/target | Credencial de serviço; somente coordinator/participantes. | 200 com account_id e erasure_id enquanto pending; 404 após complete ou para erasureId desconhecido. Sem outros dados, cache, logs ou saída persistida do Inngest. |
| POST /api/identity/browser-data-capabilities | Sessão ativa e origem válida; uso interno ao salvar rascunho. | 201 com capacidade aleatória por navegador/conta; somente seu hash e associação ficam no servidor. Não expirar enquanto a conta e rascunhos ativos dependem dela. |
| POST /identity/browser-data-validations | HTTPS, capacidade no body, sem sessão ou identidade fornecida pelo cliente. | 200 com active/revoked, sem dados da conta; token desconhecido é revoked. Falha de rede não é resposta revoked. Cache-Control: no-store e sem log do corpo. |
| POST /identity/internal/account-activity-admissions | Credencial de serviço; account_id e access_version atuais. Chamado pelo BFF somente após adquirir seu advisory lock shared na conexão Node pinada. | 204 quando a leitura sem gate confirma conta ativa/versão; 401 para conta encerrada/versão inválida; 503 para indisponibilidade. Este endpoint não adquire nem mantém o gate; a resposta não substitui o lock que permanece no BFF durante escrita/efeito. |
| POST /api/internal/identity/account-closure | Credencial de serviço; accountId e erasureId opaco, chamado depois do commit de Identity e sem manter o gate aberto. | Resultado idempotente de identidade técnica apagada. O BFF apaga sessões, contas vinculadas, usuário e verificações Better Auth na mesma transação PostgreSQL pinada; o participante só confirma após commit. |

O BFF gera o erasureId na preparação e o guarda no cookie assinado junto de
uma vinculação HMAC ao ator. O cookie tem expiração de transporte em 24 horas e
uma claim separada de 15 minutos para o primeiro fechamento. A confirmação
requer a sessão do mesmo ator e a validade curta. Se o primeiro commit ocorreu
mas a resposta se perdeu, a repetição consulta o mesmo erasureId mesmo após os
15 minutos; se não houve commit, uma tentativa expirada não fecha a conta. A
consulta pelo cookie longo chama o status Identity interno; não restaura uma
sessão nem revela se uma conta sem encerramento existe.

As respostas de erro HTTP usam erros Shifu tipados e não afirmam sucesso. A
implementação define os códigos existentes equivalentes para senha inválida,
preparação expirada, limite de tentativa, conta já encerrada e infraestrutura
indisponível; indisponibilidade antes do commit não altera a conta. O intento de
preparação e cookie de recuperação nunca substituem autenticação para enviar
dados; o cookie só permite consultar o estado.

O evento atual identity/account.deleted mantém exatamente seu payload
account_id e deleted_at; consumidores estritos não aceitam campos adicionais.
O fanout novo usa identity/account-erasure.requested com somente erasure_id
opaco. Workers obtêm accountId e erasureId por consulta interna autenticada em
cada tentativa; a resposta só existe na memória do handler e não vira entrada
ou saída de step durável. Saídas/steps do Inngest nunca contêm email, nome,
accountId, conteúdo, tokens ou payloads do aprendiz. A retenção e a remoção dos
eventos legados continuam bloqueando a afirmação de eliminação até haver prova
por serviço.

### Persistência, transações e coordenação

O gate usa advisory lock de sessão na instância PostgreSQL primária:
`pg_advisory_lock_shared` para operação normal e `pg_advisory_lock` exclusivo
para fechamento. O lock continua ativo através de commits intermediários e só
é liberado ao sair do escopo. Todos os runtimes conectam ao mesmo primário e
calculam a mesma chave por SHA-256 UTF-8 de
`shifu:account-activity:v1:<accountId>`; os oito primeiros bytes são lidos como
inteiro assinado big-endian. Não usar `hash()` de Python nem compartilhar um
PoolClient entre Node e Python. Colisão só serializa contas sem misturar dados.

Cada runtime usa sua conexão física pinada durante o escopo e suas transações
locais nessa mesma conexão. O runtime Node fixa o PoolClient por
AsyncLocalStorage para o CRUD Better Auth. O runtime Python fixa a conexão
SQLAlchemy síncrona ou assíncrona correspondente. Cada fase mantém seu dono de
commit, mas commit não libera o advisory lock de sessão. Usar pool próprio
limitado para escopos que esperam o lock; não consumir todo o pool normal.
Escopos aninhados da mesma conta reutilizam a conexão. Escopos de contas
distintas e ramos concorrentes são recusados. Erro de conexão invalida o
escopo; não obter outra conexão nem liberar uma conexão de estado incerto.

Esperar no máximo cinco segundos para adquirir o lock; timeout termina sem
efeito e retorna indisponibilidade recuperável. Nunca fazer upgrade de shared
para exclusive.

Todas as escritas e efeitos com dono de conta entram no gate, incluindo login e
emissão de sessão, Learning, avaliações, ações de mentoria, gamification,
mensagens, callbacks, jobs, cron e fanout. A operação normal mantém o gate
compartilhado durante todo o efeito remoto e o registro do resultado. Fluxos
pendentes de Identity usam a elegibilidade específica existente, mas
compartilham o mesmo gate. Jobs de purge passam erasureId e só executam em
estado encerrado. SSE adquire gate por lote de efeito, não mantém lock durante
toda a conexão.

Ordem global de bloqueio: resolve owner sem lock de linha quando a entrada só
tem email/token/attemptId; account gate; lock de email; linha Identity; locks
do módulo. Recarregar e validar owner/estado após obter o gate. Nenhum módulo
chama uma API Identity que adquire o mesmo gate enquanto o mantém.

Para emissão de sessão no BFF, autenticar primeiro pela Identity canônica.
Depois o runtime Node adquire o gate compartilhado na conexão pinada, chama
`account-activity-admissions` como leitura interna sem adquirir gate e
revalida estado/versão enquanto o gate externo está ativo. Em seguida grava a
identidade técnica/sessão na mesma conexão, faz commit e só então emite cookie.
Fechamento Identity não pode aguardar lock enquanto mantém gate no BFF; o BFF
libera seu gate antes de chamar o endpoint de fechamento.

O runtime Node fixa o PoolClient por AsyncLocalStorage durante a atividade
Better Auth; transações locais usam esse cliente, e seu release emprestado é
no-op. O runtime Python fixa sua própria conexão SQLAlchemy síncrona ou
assíncrona. Não compartilhar clientes entre runtimes. Operações não podem
escapar como tarefas destacadas; conexão invalidada não pode ser readquirida
no escopo. Não manter transação aberta em chamadas de rede.

`IdentityDatabase.account_closure_transaction` adquire o advisory lock de sessão
exclusivo na conexão do runtime Python e abre a transação Identity sobre essa
mesma conexão. O fechamento valida senha atual, identidade,
access_version e account status sob esse lock. Antes do commit, deve confirmar
que não existe receipt de efeito externo in_flight ou unknown. Receipt não
resolvido bloqueia o fechamento e deixa a conta ativa até reconciliação. A
transação Identity grava DELETED/access_version, o AccountErasure e outbox no
commit. Falha antes do commit deixa a conta ativa. Depois do commit todas as
validações de sessão falham fechadas, inclusive enquanto sessões técnicas
ainda existem. O participante BFF limpa sessões/contas Better Auth e
verificações associadas em transação pinada própria; falha mantém a conta
fechada e a limpeza pending. O endpoint nativo delete-user permanece
desabilitado porque não faz a transação conjunta exigida e não remove todas as
verificações do Shifu.

Cada efeito remoto grava receipt durável antes da chamada: effectId,
accountId operacional, operação, admittedAt e state in_flight/settled/unknown,
sem conteúdo pessoal. O gate compartilhado permanece ativo até o provedor
retornar e o receipt ser atualizado. Se um crash deixar receipt in_flight ou
unknown, o encerramento exclusivo recusa o commit e a conta continua ativa até
reconciliação. Resultado desconhecido não é sucesso nem motivo para repetir
cegamente. Após o commit, a limpeza permanece pending até todos os receipts e
participantes estarem resolvidos.

AccountErasure e participantes sobrevivem a reinício do processo. A coluna de
accountId é temporária, removida ao completar a limpeza; status mínimo por
erasureId, sem mapeamento pessoal, tem limite de 30 dias para recuperação e
operação. Ao fim do limite, não converter incidente em sucesso automático.
Apagar o accountId ausente sempre nega acesso. Email não fica em tombstone.
Migração adiciona a coordenação e índices necessários, preserva dados legados
para que a limpeza possa localizar registros e não cria FK que apague dados
de outro módulo. O owner em outbox/cache/filas deve ser consultável durante a
janela de eliminação e removido com o payload.

Cada participante expõe uma operação interna própria e confirma apenas depois
de apagar todos os dados que possui. O Identity registra participant+erasureId
com unicidade. Fanout e retry são duráveis, inicialmente com três retries
limitados e reagendamento em 1, 5, 15 e 60 minutos e depois por hora até o
deadline. Varredura periódica limitada recupera jobs perdidos. Atingir o prazo
sem ack mantém pending e cria incidente. Alerta usa template fixo por
Communication, ID estável do incidente e apenas erasureId opaco, módulo,
código seguro e datas; resultado significa aceitação pelo provedor, não prova
de entrega na caixa postal.

Gamification não abandona purges quando o perfil-raiz está ausente. Intelligence
remove o atraso que hoje espera deleted_at + 24 horas antes de começar a
limpeza de anexos. RedisPlanningSession precisa índice por conta ou lookup
equivalente sem exposição de conteúdo. Logs/operações do AgentOS não podem
manter texto pessoal nem memória após a conclusão. Communication interrompe
entrega e retries e impede callback tardio. Learning apaga tentativas,
respostas, anexos, progresso e rascunhos no servidor sem alterar Curriculum.

### Runtime Flow

    sequenceDiagram
      participant W as Web autenticada
      participant B as BFF Better Auth
      participant I as Identity
      participant DB as PostgreSQL primário
      participant Q as Inngest
      participant M as Módulos
      participant C as Browser stores

      W->>B: prepara fechamento, origem + sessão
      B->>I: emite capacidade para o navegador ativo
      I->>DB: grava hash da capacidade enquanto a conta está ativa
      B-->>W: prepared + cookie assinado de recuperação com erasureId
      W->>C: associa capacidade aos rascunhos legados locais
      W->>B: senha atual + confirmação explícita
      B->>I: POST /identity/account-deletions com bearer, senha e erasureId do cookie
      I->>DB: lock exclusivo; valida senha/versão/estado; grava DELETED, erasure e outbox
      DB-->>I: commit atômico
      I-->>B: closed / pending
      B-->>W: limpa cookie atual; sessão pública
      I->>Q: evento opaco de eliminação
      Q->>M: purge com erasureId
      Q->>B: limpa identidade técnica Better Auth
      B->>DB: transação pinada apaga sessões/contas/usuário/verificações
      B->>I: ack técnico após commit
      M->>I: ack idempotente do participante
      I->>DB: marca completed após todos os acks
      W->>B: consulta status com cookie se a resposta se perdeu
      B->>I: status por erasureId e credencial de serviço
      W->>C: valida online capacidade em reconexão
      C-->>W: revoked
      W->>C: remove IndexedDB, localStorage, query cache e notifica abas

O BFF valida sessão e origem e encaminha a confirmação à Identity. Identity
verifica a senha atual sob o gate exclusivo, compara access_version e fecha a
conta na transação que grava a solicitação durável. O BFF não mantém lock ou
transação enquanto chama a API. Depois do commit, responde closed/pending,
limpa o cookie atual e permite consulta pelo cookie de recuperação. A
coordenação chama a limpeza técnica Better Auth em uma transação separada e
marca esse participante somente após confirmação do commit. Até lá, todas as
validações de sessão consultam Identity e falham fechadas para uma conta
DELETED, mesmo que ainda exista uma linha técnica.

Antes do commit de Identity, qualquer falha é recuperável e não encerra a
conta. Depois dele, falha de módulo deixa a conta encerrada e resultado
pending. Repetição da chamada de confirmação consulta o mesmo erasureId.
Autorização indisponível é fail-closed; erro de transporte nunca é convertido
em account active para proteger shell ou emitir sessão.

# Verification Contract

## Shared setup

Backend executa de apps/server com uv; Web usa pnpm workspace web. Verificar
health e docker compose ps antes de iniciar serviços. Usar apenas infraestrutura
isolada documentada, fixture de conta Identity para validação manual e
Testcontainers/disposable fixtures para integração. Não enviar evento para
Inngest cloud, não resetar banco compartilhado e não reutilizar accountId que a
execução anterior já encerrou.

Fixtures relevantes:

- Web: apps/web/tests/fixtures/identity-module-fixture.ts;
  prepareAccountForManualValidation(runId) e limpeza correspondente.
- API/Testes: apps/server/tests/fixtures/inngest_fixture.py e fixture de
  Identity existente. Credenciais são resolvidas em código privado/ambiente;
  não incluí-las nesta Spec ou nos logs.
- Browser: Playwright CLI via apps/web; estados locais somente em
  apps/web/.playwright-cli/states/, logs em logs/, capturas em screenshots/.
  Não criar diretórios de evidência no feature.

### CI-01 — autenticação, fechamento e recuperação

**Criteria:** CA-01, CA-02, CA-06.

**Expected result:** somente senha atual e confirmação explícita fecham a
conta própria. O commit Identity bloqueia imediatamente sessões e novos
efeitos; a limpeza técnica Better Auth ocorre depois em uma transação própria.
Erro antes do commit deixa a conta ativa. Resposta perdida recupera o mesmo
estado sem PII.

**Setup / inputs:** conta ativa isolada; senha válida, inválida e mudança de
estado concorrente. Usar os limites públicos de controller/use case permitidos.

**Proof:** apps/server/tests/identity/core/use_cases/test_delete_account_use_case.py
e apps/server/tests/identity/server/controllers/test_delete_account_controller.py
(novos; executar em fronteiras permitidas). Web:
apps/web/tests/identity/account-deletion-auth-api.test.ts (novo, handler
registrado) e account-auth-api.test.ts como consumidor existente.

**Working directory:** `apps/server`.

```powershell
uv run pytest tests/identity/core/use_cases/test_delete_account_use_case.py tests/identity/server/controllers/test_delete_account_controller.py
```

**Working directory:** repository root.

```powershell
pnpm --filter web exec playwright test tests/identity/account-deletion-auth-api.test.ts tests/identity/account-auth-api.test.ts
```

**Passing condition:** assertions observam fechamento persistido, falha fechada
de sessões após o commit e limpeza técnica Better Auth confirmada; execuções
não vazias, sem autenticar por mock na jornada obrigatória.

### CI-02 — barreira, concorrência e falha fechada

**Criteria:** CA-03.

**Expected result:** login, sessão do BFF, escrita Learning, ação Intelligence,
job Gamification e entrega Communication demonstram a mesma chave e ordem
serializável antes/depois do fechamento. Timeout e falha de Identity negam sem
efeito; conta independente progride; não ocorre deadlock nem upgrade de lock.

**Setup / inputs:** PostgreSQL descartável real, barreira controlada, mesma
conta e duas contas independentes. Cobrir ambos os ordenamentos e lock timeout.

**Proof:** adicionar cenários de concorrência nas fronteiras existentes de
controller/job listadas abaixo e no novo controller de fechamento. Estender
`apps/web/tests/identity/account-auth-api.test.ts` para provar a mesma barreira
no BFF Node durante emissão de sessão. Não criar teste direto do provider ou
repository.

**Working directory:** `apps/server`.

```powershell
uv run pytest tests/identity/server/controllers/test_sign_in_controller.py tests/identity/server/controllers/test_get_current_session_controller.py tests/identity/server/controllers/test_delete_account_controller.py tests/learning/server/controllers/test_submit_choice_activity_controller.py tests/intelligence/server/controllers/test_submit_mentor_message_controller.py tests/messaging/inngest/jobs/gamification/test_create_profile_on_account_activated_job.py tests/messaging/inngest/jobs/communication/test_deliver_communication_job.py
```

**Working directory:** repository root.

```powershell
pnpm --filter web exec playwright test tests/identity/account-auth-api.test.ts
```

**Passing condition:** operação admitida termina antes de delete; operação
posterior falha; conta distinta progride; erro não deixa transação ou sessão
parcial.

### CI-03 — purge por módulo e acknowledgement

**Criteria:** CA-04, CA-05.

**Expected result:** participantes Identity, Learning, Gamification,
Intelligence e Communication apagam somente seus dados e registram ack
idempotente; ausência de raiz ou ack mantém pendente. A migration preserva
dados legados identificáveis e índices servem ao purge.

**Setup / inputs:** fixtures descartáveis com vários dados de cada módulo,
payload pendente, anexos e conta vizinha. Testar repetição e restart.

**Proof:** use cases/controllers/jobs permitidos. Criar
apps/server/tests/messaging/inngest/jobs/identity/test_coordinate_account_erasure_job.py
e
apps/server/tests/messaging/inngest/jobs/learning/test_purge_learning_data_on_account_erasure_job.py;
estender testes de purge existentes em Gamification, Intelligence e
Communication. Não testar repository/provider isoladamente.

**Working directory:** `apps/server`.

```powershell
uv run pytest tests/identity/core/use_cases/test_delete_account_use_case.py tests/messaging/inngest/jobs/identity/test_coordinate_account_erasure_job.py tests/messaging/inngest/jobs/learning/test_purge_learning_data_on_account_erasure_job.py tests/messaging/inngest/jobs/gamification/test_purge_profile_on_account_deleted_job.py tests/messaging/inngest/jobs/intelligence/test_purge_mentor_summaries_on_account_deleted_job.py tests/messaging/inngest/jobs/intelligence/test_purge_mentor_attachments_on_account_deleted_job.py tests/messaging/inngest/jobs/intelligence/test_purge_mentor_action_proposals_on_account_deleted_job.py tests/messaging/inngest/jobs/intelligence/test_purge_learner_memories_on_account_deleted_job.py tests/messaging/inngest/jobs/intelligence/test_purge_ai_quota_on_account_deleted_job.py tests/messaging/inngest/jobs/communication/test_cancel_communication_job.py tests/messaging/inngest/jobs/communication/test_deliver_communication_job.py
```

**Passing condition:** todos os dados do alvo ausentes, vizinho preservado,
ack duplicado não duplica side effects e restauração de job não recria dados.
Usar a fixture descartável existente; não disparar evento cloud.

### CI-04 — late events, receipts e idempotência

**Criteria:** CA-05, CA-07.

**Expected result:** entrega tardia, cron, callback, retry duplicado e efeito
remoto desconhecido não recriam ou repetem side effect. Resultado desconhecido
mantém pending até reconciliação.

**Setup / inputs:** reiniciar processo entre receipt in_flight e settle; repetir
evento com mesmo erasureId e enviar ack incompatível.

**Proof:** fronteiras registradas de jobs e use cases. Estender
apps/server/tests/messaging/inngest/jobs/gamification/test_create_profile_on_account_activated_job.py,
tests/messaging/inngest/jobs/communication/test_deliver_communication_job.py
(novo cenário no job existente) e testes de workflow Intelligence que possuem
efeitos remotos.

**Working directory:** `apps/server`.

```powershell
uv run pytest tests/messaging/inngest/jobs/gamification/test_create_profile_on_account_activated_job.py tests/messaging/inngest/jobs/communication/test_deliver_communication_job.py tests/messaging/inngest/jobs/identity/test_coordinate_account_erasure_job.py
```

**Passing condition:** sem perfil/entrega/proposta nova, sem duplicação; receipt
continua em estado seguro e coordinator não informa completed antes da prova.

### CI-05 — prazo, retries e alertas

**Criteria:** CA-04, CA-07, CA-11.

**Expected result:** retries respeitam agenda e deadline; falha de envio do
alerta pode ser repetida sem duplicar incidente; texto e telemetria não contêm
accountId, email ou payload pessoal.

**Setup / inputs:** relógio/falha controlados em job tests; inspecionar
mensagem renderizada apenas com valores não pessoais.

**Proof:** use case de coordenação e jobs/consumer Communication permitidos.
Adicionar testes em
apps/server/tests/messaging/inngest/jobs/identity/test_sweep_account_erasure_job.py
e fronteira de entrega Communication.

**Working directory:** `apps/server`.

```powershell
uv run pytest tests/messaging/inngest/jobs/identity/test_sweep_account_erasure_job.py tests/messaging/inngest/jobs/communication/test_deliver_communication_job.py
```

**Passing condition:** agenda e deadline observáveis, alerta sem campos
proibidos, estado nunca pula de pending para completed sem todos os acks.

### CI-06 — BFF, sessão Better Auth e reutilização de email

**Criteria:** CA-01, CA-02, CA-06.

**Expected result:** Better Auth CRUD participa da conexão pinada; a exclusão
técnica posterior remove sessions/accounts/user/verifications em uma única
transação; endpoint nativo continua
desabilitado; fallback de identidade indisponível não autoriza shell nem
sessão.

**Setup / inputs:** handlers de autenticação registrados, PostgreSQL
descartável, resposta do auth store em 0/429/5xx e email reutilizado.

**Proof:** apps/web/tests/identity/account-deletion-auth-api.test.ts,
apps/web/tests/identity/account-auth-api.test.ts e
apps/web/src/ui/shared/contexts/auth-context/tests/use-auth-context-provider.test.ts
(novos cenários ou teste existente).

**Working directory:** repository root.

```powershell
pnpm --filter web exec playwright test tests/identity/account-deletion-auth-api.test.ts tests/identity/account-auth-api.test.ts
pnpm --filter web exec vitest run src/ui/shared/contexts/auth-context/tests/use-auth-context-provider.test.ts
```

**Passing condition:** email novo cria accountId novo; conta antiga não
autentica; indisponibilidade nunca restaura acesso.

### CI-07 — capacidade de browser e armazenamento local

**Criteria:** CA-08.

**Expected result:** capability ativa/revogada/desconhecida é tratada sem PII;
capacidade não substitui sessão; revogação remove rascunho IndexedDB, aviso de
quota local, cache e memória por conta; falha de rede preserva e bloqueia
restauração/envio.

**Setup / inputs:** stores IndexedDB descartáveis, duas abas, rascunho antigo
sem capability, conta ativa e revogada, network error e 401.

**Proof:** testes consumidores dos widgets e da página em
apps/web/src/ui/identity/widgets/pages/account-deletion-page/deletion-panel/tests/deletion-panel.test.tsx,
use-deletion-panel.test.ts e
apps/web/src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx
e use-activity-page.test.ts. Endpoint via teste do handler registrado em CI-06;
sem teste direto do action hook ou adapter IndexedDB.

**Working directory:** repository root.

```powershell
pnpm --filter web exec vitest run src/ui/identity/widgets/pages/account-deletion-page/deletion-panel/tests/deletion-panel.test.tsx src/ui/identity/widgets/pages/account-deletion-page/deletion-panel/tests/use-deletion-panel.test.ts src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx src/ui/learning/widgets/pages/activity-page/tests/use-activity-page.test.ts
```

**Passing condition:** marcador revogado é persistido antes de limpeza;
operações futuras respeitam o marcador; tab vizinha não ressuscita dados; rede
indisponível nunca vira confirmação.

### CI-08 — widget composto, accessibility e feedback visível

**Criteria:** CA-01, CA-02, CA-08, CA-09, CA-10.

**Expected result:** estados de senha, preparação, erro, fechamento e
eliminação são distintos; senha/consentimento limpam no cancelamento; teclado,
foco, aria e tamanhos responsivos passam nos consumidores.

**Setup / inputs:** composição real de página/painel com transportes
controlados; perfil existente, interrupção, retry e retorno pela rota.

**Proof:** arquivos existentes
apps/web/src/ui/identity/widgets/pages/account-deletion-page/deletion-panel/tests/deletion-panel.test.tsx,
use-deletion-panel.test.ts e apps/web/tests/identity/account-deletion-page.test.ts.

**Working directory:** repository root.

```powershell
pnpm --filter web exec vitest run src/ui/identity/widgets/pages/account-deletion-page/deletion-panel/tests/deletion-panel.test.tsx src/ui/identity/widgets/pages/account-deletion-page/deletion-panel/tests/use-deletion-panel.test.ts
pnpm --filter web exec playwright test tests/identity/account-deletion-page.test.ts
```

**Passing condition:** fluxo real de widget montado, assertions de requests,
cache/resultado, teclado e estados; nenhuma seleção vazia ou teste só do helper.

### CI-09 — gates de tipo, lint, arquitetura, complexidade e build

**Scope:** apps/web e apps/server e consumidores afetados.

**Checks:** executar no diretório `apps/web`: `pnpm run generate-routes`,
`pnpm run check:types`, `pnpm run check:lint`, `pnpm run check:architecture` e
`pnpm run build`.
Executar no diretório `apps/server`: `uv run poe check:types`,
`uv run poe check:lint`, `uv run poe check:architecture` e `uv run poe build`.
Na raiz, reexecutar `pnpm check:test-integrity` para as novas fronteiras. Usar
lint focado nos paths alterados antes dos gates do app.

**Complexidade:** Ruff C90 é obrigatório nos paths Python tocados. Biome
complexity faz parte do check:lint Web nos paths tocados. Não há runner de
métrica quantitativa; não inventar score/command. Registrar como Blocked
qualquer novo gate obrigatório indisponível, sem esconder avisos.

**Passing condition:** zero erros e avisos novos nos paths afetados; todos os
comandos existem no manifest atual, os testes selecionados executam e a
arquitetura mantém Shared sem regras de negócio.

## Manual

### VM-01 — validar e preparar exclusão por teclado

**Type:** Manual

**Criteria:** CA-01, CA-09, CA-10

**Tool / setup:** da pasta `apps/web`, verificar serviços e health checks e
abrir `playwright-cli -s=shifu open http://127.0.0.1:7000/account/delete`.
Usar uma conta ativa isolada de `prepareAccountForManualValidation`; se a sessão
local não existir, autenticar pela tela visível. Desktop 1440×900 e mobile
390×844. Guardar capturas em `.playwright-cli/screenshots/` e observações em
`.playwright-cli/logs/`.

**Procedure:** abrir /account/delete; navegar com Tab; consultar consequências
e política sem confirmar; testar senha incorreta, confirmação ausente e
cancelamento; verificar limpeza de campos e retorno de foco.

**Passing condition:** destino/página corretos, nenhuma chamada destrutiva,
nenhum conteúdo pessoal na URL, request ou console; modal e página utilizáveis
por teclado sem overflow. Remover estado isolado pela fixture.

### VM-02 — fechar conta e recuperar status

**Type:** Manual

**Criteria:** CA-02, CA-06, CA-09

**Tool / setup:** da pasta `apps/web`, abrir
`playwright-cli -s=shifu open http://127.0.0.1:7000/account/delete` em ambiente
isolado, com sessão autenticada real da fixture e banco descartável. Guardar
capturas em `.playwright-cli/screenshots/` e observações em
`.playwright-cli/logs/`.

**Procedure:** preparar, confirmar senha e consentimento, verificar navegação
para estado público; tentar sessão antiga e consultar o status com cookie de
recuperação; repetir consulta depois de reload.

**Passing condition:** acesso antigo negado, estado closed/pending ou completed
coerente com acknowledgements e nenhum PII no resultado; conta nova com o
mesmo email é independente. Não usar conta de pessoa real.

### VM-03 — rascunho offline e reconexão

**Type:** Manual

**Criteria:** CA-08

**Tool / setup:** Playwright CLI com duas abas do mesmo navegador, rascunho
IndexedDB da conta isolada e capacidade válida; iniciar pela página
`/account/delete` conforme VM-01. Guardar artefatos nos diretórios
`.playwright-cli/` documentados em VM-01.

**Procedure:** criar rascunho, desconectar a rede, fechar/abrir atividade sem
limpar o dado; concluir o encerramento em sessão online separada; reconectar a
aba antiga e consultar capacidade; repetir com network failure e sessão
expirada.

**Passing condition:** offline/falha preserva e bloqueia envio/restauração;
resposta revoked limpa todas as abas e quota/cache da conta; sem mensagem de
exclusão concluída antes da confirmação.

## Visual

### VM-04 — página e estados de exclusão

**Type:** Visual

**Criteria:** CA-09, CA-10

**Reference / setup:** bloqueado até conectar o Penpot Shifu. Registrar a
página, boards, componentes e estados reais após inspeção MCP; referências
Pencil antigas são históricas. Viewports 1440×900 e 390×844.

**Capture / comparison:** export fresco dos boards via Penpot MCP comparado às
capturas Playwright dos mesmos estados/viewport. Reutilizar capturas VM-01/02
quando atuais.

**Passing condition:** hierarquia, espaçamento, tokens, tipografia, contraste,
alvos de toque, contenção e estados correspondem aos boards. Nenhum resultado
até referência atual ser acessível; uma captura isolada não prova persistência.

# Documentation Alignment

| Documento / autoridade | Governa | Atualização ou confirmação | Disposição / dependência |
| --- | --- | --- | --- |
| Jira SHIFU-98, Dev Task, pai SHIFU-24, atualizado em 2026-11-01 | escopo completo, critérios e exclusões | Usar como ticket de entrega, sem editar Jira. Jira ainda aponta PRD Identity v2 e política v2; essas referências são históricas. | https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-98 |
| Shifu — PRD — Identity, contentId 83001345, v6, atualizado 2026-11-20T20:00:16.502Z; lido completo em 2026-11-20 21:00 UTC | RP-01/RP-07/RP-09/RP-10; JN-09/JN-10 | Aditivo SHIFU-98 aprovado foi publicado e relido. | https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83001345/Shifu+PRD+Identity |
| Shifu — PRD — Learning, contentId 83066881, v34, atualizado 2026-11-20T20:00:32.423Z; lido completo em 2026-11-20 21:00 UTC | RP-09/RP-14/RP-23/RP-29 | Aditivo SHIFU-98 aprovado foi publicado e relido. | https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83066881/Shifu+PRD+Learning |
| Shifu — PRD — Communication, contentId 86114306, v4, atualizado 2026-11-11T23:24:00.370Z; lido completo em 2026-11-21 | Catálogo de tipos/canais e destinatários de Communication; RP-02 | O PRD limita o catálogo a tipos aprovados e exige inclusão explícita de tipos novos; o alerta operacional da CA-11 não consta no catálogo v4. | BLOQUEIO: reconciliar CA-11 pelo create-spec e obter o aditivo/autoridade aplicável antes de declarar alinhamento. Não alterar Confluence sem pedido explícito. https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/86114306/Shifu+PRD+Communication |
| Shifu — Política de Privacidade e Ciclo de Vida dos Dados, contentId 100106241, v4, atualizado 2026-10-08T01:07:15.769Z; lido completo em 2026-11-20 21:00 UTC | Prazo dos dados ativos, logs, backups, responsabilidade dos módulos e canal operacional | Aditivo aprovado ainda não foi publicado. O readback permanece v4 sem o texto; atualização retornou internal_error e, após refetch do draft d1:156, snapshot_stale. Não declarar política alinhada. | BLOQUEIO: resolver conflito de autoridade e reler a página completa antes de marcar ready. https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/100106241 |
| Regras e arquitetura | fronteiras Shared/Core/Identity, SQLAlchemy, REST, jobs, UI, routing e testes | documentation/rules.md, architecture.md, modules.md, tooling.md, sdd.md e Rule Packs selecionados lidos; sem alteração. .codegraph/ não existe na raiz desta worktree. | Revalidar roteamento dinâmico se escopo crescer. |
| Inngest oficial | retenção e remoção de eventos, steps e execuções que podem conter dados pessoais | Os docs Cloud atuais dizem que a API de remoção baseada em `user.external_id` ainda é futura; a retenção exata depende do plano. Se self-hosted com PostgreSQL, o servidor não apaga automaticamente rows antigos de eventos, runs ou traces; comandos/guias de retenção ainda estão planejados. Payloads de evento e saídas de `step.run` são armazenados. | BLOQUEIO: identificar o modo de implantação do Shifu e obter prova de retenção/remoção no prazo de 24 horas para payloads legados; cancelamento não é prova de eliminação. https://www.inngest.com/docs/reference/typescript/events/send ; https://www.inngest.com/docs/platform-and-operations/cloud-architecture-and-security ; https://www.inngest.com/docs/durable-execution/limits ; https://www.inngest.com/docs/self-hosting ; https://www.inngest.com/docs/durable-execution/guides-and-advanced/cancellation |
| Penpot Shifu | referência visual de UI para página, confirmação e estados de resultado | Nenhum board atual foi lido. Em 2026-11-20 o perfil dedicado foi aberto e o usuário informou que não conectará o arquivo/plugin nesta etapa. Não usar Pencil histórico. | BLOQUEIO: nomes dos boards e comparação visual pendentes até a conexão ser solicitada pelo usuário. |
| Shifu SDD, templates e Rules | estrutura do documento, provas, compatibilidade e ownership | Seguidos os sete headings canônicos e Rule Packs selecionados. | Criar evaluation.md apenas no início da implementação. |

# Revision History

| Revisão | Data | Mudança contratual | Motivo / fonte |
| --- | --- | --- | --- |
| 1 | 2026-11-20 | Spec inicial completa para encerramento, eliminação coordenada, barreira de atividade e rascunhos offline. | Jira SHIFU-98; Identity v6; Learning v34; decisões aprovadas pelo usuário. Mantida draft por conflito da política v4, dependência de retenção Inngest e referência Penpot não verificada. |
| 2 | 2026-11-20 | Precisados a admissão concorrente Node/Python, a resolução opaca de erasureId, as tentativas de recuperação, os efeitos externos incertos e os checkers Playwright/Vitest. | Revisão independente e docs oficiais atuais do Inngest; Penpot permanece bloqueado após recusa de conexão nesta etapa. |
| 3 | 2026-11-21 | Explicitados o retry durável do participante BFF, a admissão de novas filas de Communication e a remoção dos eventos Intelligence com accountId no purge dono. | Revisão independente encontrou caminhos capazes de deixar conta pendente ou payload pessoal após acknowledgement. |

Follow documentation/sdd.md e documentation/prompts/create-spec-prompt.md.

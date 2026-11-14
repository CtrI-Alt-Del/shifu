---
title: SHIFU-98 — interface de exclusão de conta
status: implemented
revision: 1
source:
  type: direct-request
  ref: SHIFU-98; pedido de preparar pelo menos a UI
scope:
  - Identity Web
last_updated_at: 2026-10-25
---

# Objective

Entrega compacta da interface de exclusão em Minha conta. Preparar a aba e a confirmação conforme o Pencil, sem executar exclusão ou apresentar sucesso fictício. O pedido do usuário autoriza esta entrega parcial; revisão independente do contrato sem bloqueios em 25/10/2026; a exclusão completa continua pendente na SHIFU-98.

# Scope

RP-09 e JN-09 parcialmente implementados: avisos e preparação visual da confirmação. RP-10 aplicado à interface. Encerramento, verificação da senha no servidor, eliminação, repetição de operações, reutilização de e-mail e JN-10 ficam adiados. Nenhum endpoint, sessão, banco, job ou política pública é alterado.

Referências e adaptações: [handoff](design/handoff.md).

# Behavior Contract

| ID | Fonte | Comportamento |
| --- | --- | --- |
| RF-01 | RP-09, JN-09; pedido de UI parcial | Minha conta inclui Excluir conta e um cartão que abre o modal. |
| RF-02 | RP-09, JN-09 | Explicar exclusão definitiva, bloqueio imediato e eliminação ativa em até 24 horas após o futuro encerramento. Oferecer política e contato existentes. Mostrar explicitamente que a exclusão ainda está indisponível. |
| RF-03 | RP-09, RP-10 | Modal com senha atual, mostrar/ocultar, confirmação explícita e cancelar. A confirmação final permanece desabilitada em todos os estados. Nenhuma chamada de exclusão, persistência de senha, encerramento de sessão ou sucesso simulado. |
| RF-04 | RP-10 | Desktop/mobile e teclado. Fechar, Escape, troca de aba e reabertura descartam senha e consentimento. Foco protegido e devolvido ao gatilho ao cancelar. |

| CA | RF | Dado / Quando / Então | Checkers |
| --- | --- | --- | --- |
| CA-01 | RF-01 | Conta carregada, selecionar Excluir conta mostra o cartão e permite abrir o modal sem alterar Perfil/Segurança. | CI-01, CI-02, VM-01 |
| CA-02 | RF-02 | Cartão/modal abertos explicam consequências, prazo condicionado ao encerramento futuro, indisponibilidade e acesso à política. Abrir política não confirma exclusão. | CI-01, CI-02, VM-01 |
| CA-03 | RF-03 | Com senha vazia/preenchida e consentimento desligado/ligado, confirmação sempre indisponível e nenhum efeito destrutivo ou envio de senha. | CI-01, CI-02 |
| CA-04 | RF-04 | Cancelar/Escape/trocar aba e reabrir limpam os campos; teclado, foco e viewport 390×844 funcionam sem transbordamento horizontal. | CI-01, CI-02, VM-01, VM-02 |

# Technical Contract

## Architecture Mapping

Identity mantém a propriedade. Reutilizar Tabs, Dialog, Input, Label, Checkbox, Button, Icon e Anchor existentes. O botão final usa variant='danger'; gatilho neutro com borda/ícone selo. Não introduzir abstração de serviço ou opção que permita habilitar exclusão sem implementação completa.

| Ação | Limite | Elemento / caminho | Mudança |
| --- | --- | --- | --- |
| Modify | Página Identity | apps/web/src/ui/identity/widgets/pages/account-page/{index.tsx,use-account-page.ts} | Terceira aba e painel. Hook controla profile/security/delete. |
| Create | Widget Identity | account-page/deletion-panel/{index.tsx,use-deletion-panel.ts} | Hook controla abertura, senha, visibilidade e consentimento locais. A página monta o painel somente na aba ativa; desmontar descarta todo o estado local. |
| Modify/Create | Testes dos consumidores | account-page/tests/, deletion-panel/tests/, apps/web/tests/identity/account-page.test.ts | Provar UI composta, transições e ausência de efeitos. |

## Arquivos afetados

```text
apps/web/src/ui/identity/widgets/pages/account-page/
  index.tsx [M]
  use-account-page.ts [M]
  tests/account-page.test.tsx [M]
  tests/use-account-page.test.ts [M]
  deletion-panel/
    index.tsx [N]
    use-deletion-panel.ts [N]
    tests/deletion-panel.test.tsx [N]
    tests/use-deletion-panel.test.ts [N]
apps/web/tests/identity/account-page.test.ts [M]
```

Os testes existentes de profile-form e security-form integram a seleção CI-01 como consumidores diretamente afetados pela nova aba. Nenhum arquivo gerado muda.

## Runtime Flow

Autenticação e carregamento da conta continuam no fluxo existente. Selecionar a aba renderiza o cartão. Abrir o modal mantém os dados somente na memória do widget. Os campos preparam a composição visual, sem validar credenciais remotamente. Cancelar ou sair da aba limpa a memória. O botão final não possui ação de envio. A política usa o destino público existente e não transporta a senha. Não existe transação ou efeito externo novo.

# Verification Contract

## Shared setup

Node 24.20.0 e pnpm existentes. Testes de rota usam a fixture Identity e transportes controlados existentes. Validação manual usa conta ativa isolada criada por prepareAccountForManualValidation em tests/fixtures/identity-module-fixture.ts, login visível via Playwright CLI e limpeza pela função correspondente. Não reiniciar dados compartilhados. Capturas em apps/web/.playwright-cli/screenshots/; logs em logs/.

## Automated

- CI-01: de apps/web, `pnpm test:unit src/ui/identity/widgets/pages/account-page`. CA-01–04. Testes dos hooks e componentes com os limites de mock exigidos pelas regras. Incluir matriz senha/consentimento, cancelamento e descarte. Sem loading/erro/sucesso de exclusão porque não existe operação nesta fatia.
- CI-02: de apps/web, `pnpm test:integration tests/identity/account-page.test.ts`. CA-01–04. Rota real com transporte controlado, teclado, mobile, política e ausência de chamadas destrutivas.
- CI-03: de apps/web, `pnpm check:types`. Projeto consumidor completo sem erros.
- CI-04: de apps/web, `pnpm check:lint`. Lint/formatação sem erros. Registrar avisos preexistentes separadamente.
- CI-05: complexidade configurada no Biome, mesma execução CI-04, sem novos diagnósticos nos caminhos alterados. Não há runner quantitativo configurado; métricas quantitativas não são obrigação desta entrega.
- CI-06: de apps/web, `pnpm check:architecture` e `pnpm build`. Limites de dependências válidos e build concluído.

## Manual

VM-01 (Manual, CA-01–04): Playwright CLI, login real na conta isolada. Abrir /account, navegar por teclado até a aba e abrir modal. Preencher senha de teste, alternar confirmação, verificar botão bloqueado, cancelar, reabrir e verificar limpeza. Consultar política e verificar destino público. Conferir requests/console. Repetir apresentação em 390×844. Nenhuma exclusão real é solicitada.

## Visual

VM-02 (Visual, CA-01, CA-02, CA-04): comparar cartão e modal desktop 1440×900 e mobile 390×844 com os dois quadros do handoff. Inspecionar quatro capturas. Aceitar somente adaptações documentadas de shell, aviso de indisponibilidade, botão final danger e coluna mobile. Revisão independente de implementação e visual em paralelo no mesmo candidato.

# Documentation Alignment

| Autoridade | Identidade / disposição |
| --- | --- |
| PRD Identity | Confluence 83001345, v2, lido integralmente em 25/10/2026. RP-09/RP-10, JN-09. https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83001345 |
| Jira | SHIFU-98, escopo integral permanece pendente; esta fatia não conclui o ticket. https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-98 |
| Regras | documentation/{sdd,rules,design,tooling,modules,architecture}.md; rules/{ui-layer,typescript-conventions,widget-testing}-rules.md. Sem alterações dessas autoridades. |
| Pencil | design/shifu.pen, y2vJij e LbeWb; leitura MCP, sem editar o design. |
| SHIFU-97 | Preservar contrato e documentos concluídos no worktree anterior. A omissão da aba deixa de ser aplicável nesta nova fatia. |

Nenhuma escrita Jira/Confluence. Commit, push e PR separado autorizados pelo usuário após a validação local.

# Revision History

- 1 — 25/10/2026: fatia de UI solicitada pelo usuário, com execução destrutiva explicitamente indisponível.

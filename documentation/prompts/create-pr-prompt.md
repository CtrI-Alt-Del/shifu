---
name: create-pr
description: Publicar ou atualizar um Pull Request do Shifu com rastreabilidade de Jira, PRD e SDD, além de evidências atuais de validação.
---

# Prompt: Criar ou Atualizar Pull Request

## Objetivo

Publicar uma entrega coerente do Shifu no GitHub. Use `gh`, preserve a worktree
do usuário e atualize um PR existente da mesma entrega em vez de criar uma
duplicata.

Esta tarefa não cria Spec, PRD, Plan, Evaluation ou ticket Jira. Apenas consome
os documentos existentes e a demanda direta quando a entrega não tiver
documentação SDD.

## Entradas e fontes de autoridade

Leia, quando existirem e forem aplicáveis:

- ticket Jira da entrega;
- PRD canônico completo no Confluence;
- Spec ou Bug Report implementado;
- Plan;
- `evaluation.md`;
- diff real da entrega;
- `documentation/sdd.md`;
- `documentation/architecture.md`;
- `documentation/modules.md`;
- rules selecionadas por `documentation/rules.md`;
- `documentation/rules/commit-rules.md`.

Quando a entrega vier de uma Spec, confirme que o `evaluation.md` segue o
template canônico e possui evidências atuais para a revisão exata da Spec.
Quando vier de uma demanda direta, não invente Spec, PRD, Jira, requisitos ou
registros externos para preencher o PR.

Exija autorização explícita antes de fazer commit, `push` e criar ou atualizar
o PR. A invocação explícita deste prompt autoriza o `push` e a publicação do PR,
mas não autoriza commits de alterações pendentes. No uso independente, invoque
`commit-code` somente quando o usuário também autorizar os commits. Quando
chamado por `conclude-spec`, reutilize os commits preparados imediatamente pelo
`commit-code` do mesmo handoff; não crie commits adicionais nem invoque
`commit-code` novamente.

## Inspeção da entrega

Antes da publicação, inspecione a worktree completa e o histórico:

```bash
git status --short
git diff --stat
git diff
git diff --cached --stat
git diff --cached
git log -10 --format='%h %s'
```

Identifique:

- arquivos em stage, modificados e não rastreados;
- artifacts gerados, migrations, seeds, lockfiles e configurações;
- aplicações, packages e módulos afetados;
- alterações do usuário sem relação com a entrega;
- segredos ou dados locais que não podem entrar no PR;
- divergências entre Jira, PRD, Spec, implementação e evidências.

Preserve alterações alheias e mantenha-as fora dos commits. Se a relação entre
um arquivo e a entrega for ambígua, interrompa e informe a ambiguidade em vez de
incluí-lo por suposição.

## Preparação da branch e do PR

1. Confirme que a branch não é `main` nem `production`.
2. Inspecione as alterações em stage e fora dele.
3. Confirme que os commits autorizados da entrega estão concluídos.
4. Exija worktree limpa antes de incorporar `main`. Alterações alheias devem ser
   preservadas pelo usuário; não faça stash, reset, restore ou checkout delas.
5. Busque a branch real de integração sem trocar a worktree:

   ```bash
   git fetch origin main --prune
   ```

6. Consulte PRs abertos e fechados pela head branch e por termos do Jira ou da
   entrega.
7. Verifique base, head, SHA e ancestralidade; o nome da branch não comprova
   incorporação.
8. Use `main`/`origin/main` como base, salvo instrução explícita diferente.
9. Incorpore obrigatoriamente o `origin/main` mais recente conforme a próxima
   seção.
10. Calcule e revise o diff completo contra a base após o merge.
11. Atualize o PR existente da mesma entrega ou crie um único PR novo.

Não use operações Git destrutivas, não ignore hooks, não crie branches
dependentes acidentalmente e não misture alterações sem relação.

## Sincronização obrigatória com `main`

Antes de criar ou atualizar o PR, faça merge do `origin/main` mais recente na
branch da entrega. Não substitua por rebase.

Com a worktree limpa:

```bash
git fetch origin main --prune
git merge --no-edit origin/main
```

Após um merge sem conflitos, revise o diff resultante e repita as validações
afetadas pelo conteúdo incorporado.

Resolva automaticamente apenas conflitos mecânicos e inequívocos, como
formatação, ordenação de imports, documentação independente ou artifact gerado
por comando oficial determinístico. Inspecione os três lados, preserve a
intenção de `main` e da entrega, adicione somente os paths resolvidos e execute
novamente os checks afetados.

Interrompa e solicite orientação quando houver conflito de regra de negócio,
contrato público, schema, migration, persistência, autenticação, autorização,
segurança, dependência, lockfile, workflow, infraestrutura, teste funcional ou
arquivo removido de um lado e modificado do outro. Não faça `git add`, commit,
`push` ou publicação enquanto a resolução for ambígua e não aborte o merge sem
pedido explícito.

Imediatamente antes da publicação:

```bash
git fetch origin main --prune
git merge-base --is-ancestor origin/main HEAD
```

Não publique enquanto `origin/main` não for ancestral do `HEAD`.

## Evidências de validação

Use evidências atuais e execute somente checks adicionais aprovados pelo
repositório e necessários ao estado de publicação. Use os comandos dos
manifests, regras e documentação atuais; não substitua comandos exatos por
alternativas presumidas.

Quando houver Spec, confirme:

- revisão exata e estado da Spec;
- paths alterados dentro do escopo registrado;
- contratos e critérios atendidos;
- evidências atuais para cada critério;
- disposição registrada no `evaluation.md` sem sugerir alteração no
  Confluence.

Se a conformidade falhar, interrompa a publicação e encaminhe a correção pelo
workflow aplicável. Não corrija implementação ou contrato silenciosamente
dentro do fluxo de criação do PR.

Para UI baseada em design, use o bundle salvo pela Spec e as evidências do
`evaluation.md`. Resuma a validação visual em `## Testes manuais`; não crie uma
seção separada de evidências visuais.

Revise migrations, artifacts gerados e lockfiles quando afetados. Não declare
como executado um check, fluxo manual, review ou deploy que não foi observado.
Registre falhas, limitações de ambiente e comandos omitidos como limitações, não
como sucesso.

## Artifacts gerados e migrations

Quando a entrega alterar persistência ou conteúdo gerado:

- compare migrations, snapshots e metadados com `origin/main`;
- resolva colisões preservando entradas anteriores;
- execute uma vez o comando oficial de geração ou verificação;
- revise o resultado contra sua fonte;
- inclua derivados somente quando necessários e atuais.

Nunca edite artifacts gerados manualmente para ocultar divergências nem trate
falha de geração como check aprovado.

## Contrato do PR

O título e todo o body devem ser escritos em pt-BR. O body deve usar as seções
abaixo, nesta ordem.

### Objetivo

```markdown
## Objetivo
```

Descreva o problema, o resultado esperado, o escopo e exclusões relevantes.

### PRD

```markdown
## PRD
```

Liste as URLs completas dos PRDs canônicos no Confluence e seus content IDs e
versões. Quando não houver PRD aplicável, escreva:

```markdown
## PRD

Não aplicável — alteração exclusivamente técnica.
```

### Requisitos afetados

Inclua somente quando houver PRD. Liste apenas identificadores reais, como
`RP-*` e `JN-*`, com descrição resumida quando conhecida.

### Jira

```markdown
## Jira
```

Liste somente tickets reais por URL completa. Não declare que o merge encerra
ou transiciona um ticket, salvo quando isso fizer parte de uma automação
confirmada. Quando não houver ticket, escreva `Não aplicável.`

### Implementação técnica

```markdown
## Implementação técnica
```

Resuma os recortes coerentes de frontend, backend, domínio, persistência,
mensageria, infraestrutura e testes, citando apenas os paths mais relevantes.

### Alterações de regras de negócio

Inclua somente quando comportamento, validação, autorização ou workflow de
produto forem alterados. Registre comportamento anterior, novo comportamento,
motivo e evidência.

### Testes manuais

```markdown
## Testes manuais
```

Informe pré-requisitos, passos reproduzíveis, resultado esperado e fluxos de
erro ou recuperação. Quando não aplicável, diga explicitamente.

### Validações automatizadas

```markdown
## Validações automatizadas
```

Liste comandos exatos e resultados observados, incluindo falhas, limitações e
checks omitidos.

### Migrations e artifacts gerados

```markdown
## Migrations e artifacts gerados
```

Liste os itens revisados e seus comandos de geração/verificação ou escreva
`Não aplicável.`

### Limitações conhecidas

```markdown
## Limitações conhecidas
```

Registre lacunas, riscos, divergências de escopo e trabalho restante, ou escreva
`Nenhuma.`

Não adicione seções genéricas como `Changelog`, `Impacto e compatibilidade`,
`Observações`, `Evidências visuais` ou `Codex Review Summary`. Não copie o diff
inteiro nem invente tickets, requisitos, testes ou aprovações humanas.

## Título

Use uma frase nominal curta em pt-BR, sem prefixo de Conventional Commit. Quando
houver ticket Jira, prefixe obrigatoriamente com a chave entre colchetes:

```text
[SHIFU-71] Modelagem dos objetos de domínio principais
```

Quando não houver Jira, use apenas a frase nominal. Nunca invente uma chave.

## Publicação e retorno

Faça `push` da branch preparada e crie ou atualize o PR com `gh`. Não faça merge
nem deploy.

### Conversas de review

Ao criar ou atualizar um PR existente, inspecione suas conversas de review antes
de concluir a tarefa. Para cada conversa cujo pedido foi implementado na revisão
atual e validado pelos checks aplicáveis, marque a thread como resolvida no
GitHub usando a mutação autenticada de `gh`, inclusive quando a thread estiver
obsoleta por uma alteração posterior. Não marque como resolvida uma conversa sem
evidência de que o pedido foi atendido; registre-a como pendência e encaminhe-a
para `resolve-pr-feedback`.

Resolver uma thread não substitui uma nova revisão humana. Retorne
separadamente a contagem de threads resolvidas e o estado `reviewDecision` do
GitHub, preservando `CHANGES_REQUESTED` quando o revisor ainda não tiver
reavaliado o PR.

Depois, leia o PR publicado:

```bash
gh pr view <numero> \
  --json number,url,title,headRefName,baseRefName,headRefOid,commits,statusCheckRollup,reviewDecision,reviews
```

Retorne:

- URL e número do PR;
- título, base, head e head SHA;
- resumo dos módulos e paths alterados;
- Jira, PRDs e requisitos afetados;
- estado atual dos checks e reviews;
- limitações ou alterações locais preservadas.

Comentários posteriores de review são classificados e corrigidos por
`resolve-pr-feedback`; ao publicar a correção validada, este prompt também
conclui a resolução das threads correspondentes.

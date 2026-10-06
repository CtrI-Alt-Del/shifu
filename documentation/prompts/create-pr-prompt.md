---
name: create-pr
description: Publicar ou atualizar um Pull Request do Shifu com rastreabilidade de Jira, PRD e SDD, além de evidências atuais de validação.
---

# Prompt: Criar ou Atualizar Pull Request

## Objetivo

Publicar uma entrega coerente do Shifu no GitHub. Use `gh`, preserve a worktree
do usuário e atualize um PR existente da mesma entrega em vez de criar uma
duplicata.

Esta tarefa não cria Spec, PRD, Evaluation ou ticket Jira. Apenas consome
os documentos existentes e a demanda direta quando a entrega não tiver
documentação SDD.

## Entradas e fontes de autoridade

Leia, quando existirem e forem aplicáveis:

- ticket Jira da entrega;
- PRD canônico completo no Confluence;
- Spec ou Bug Report implementado;
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

### Documentação e fontes de design

Inclua no PR a documentação alterada que fundamenta, especifica ou registra a
entrega, mesmo quando o diff for somente documental. Isso inclui os artifacts
SDD aplicáveis, handoff e referências, além de atualizações relacionadas em
`AGENTS.md`, Arquitetura, Design, Rules e prompts. Não deixe esses arquivos
alterados apenas na worktree por parecerem documentação auxiliar.

Inclua também os arquivos-fonte Pencil `.pen` modificados ou fornecidos para a
entrega. Trate-os como artifacts opacos: nunca abra, leia, compare, procure ou
edite seus bytes com shell ou ferramentas genéricas de filesystem. Use Pencil
MCP para inspeção ou edição visual; para publicação, identifique e adicione o
path exato como arquivo versionado sem expor seu conteúdo. Preserve arquivos
Pencil que não pertençam à entrega atual.

## Preparação da branch e do PR

1. Confirme que a branch não é `main` nem `production`.
2. Inspecione as alterações em stage e fora dele.
3. Confirme que os commits autorizados da entrega estão concluídos.
4. Preserve alterações alheias. Se um merge necessário não puder preservá-las
   com segurança, reporte o bloqueio; não faça stash, reset, restore ou checkout.
   Uma sincronização já incorporada não exige worktree limpa.
5. Verifique o remote configurado da entrega e sua branch real `main`; reutilize
   a mesma autoridade remota de `conclude-spec`. Busque esse ref sem trocar a
   worktree. Use `origin` apenas quando for o remote verificado.

6. Consulte PRs abertos e fechados pela head branch e por termos do Jira ou da
   entrega.
7. Verifique base, head, SHA e ancestralidade; o nome da branch não comprova
   incorporação.
8. Use `main` do remote verificado como base, salvo instrução explícita diferente.
9. Incorpore o `main` mais recente desse remote conforme a próxima
   seção.
10. Calcule e revise o diff completo contra a base após o merge.
11. Atualize o PR existente da mesma entrega ou crie um único PR novo.

Não use operações Git destrutivas, não ignore hooks, não crie branches
dependentes acidentalmente e não misture alterações sem relação.

## Sincronização obrigatória com `main`

Antes de criar ou atualizar o PR, faça merge do `main` mais recente do remote verificado na
branch da entrega. Não substitua por rebase.

Substitua `<remote>` e `<remote-main-ref>` pelos valores verificados. Inspecione
a worktree e só prossiga quando Git puder preservar todas as alterações:

```bash
git fetch <remote> main --prune
git merge --no-edit <remote-main-ref>
```

Faça essa sincronização antes da verificação integrada final sempre que possível.
Quando chamado por `conclude-spec`, reutilize a sincronização já realizada se o
ref remoto mais recente já estiver incorporado. Após o merge, inspecione o diff
e invalide apenas evidências cujo contrato, código coberto, dependências, fixtures
ou configuração foram afetados. Um novo SHA ou merge sem mudança nessas
superfícies não exige repetir suítes. Encaminhe checks afetados ao runner de
verificação designado pelo Orchestrator e aguarde resultados aprovados antes de publicar.

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
git fetch <remote> main --prune
git merge-base --is-ancestor <remote-main-ref> HEAD
```

Não publique enquanto o `main` do remote verificado não for ancestral do `HEAD`.

## Evidências de validação

Consuma os resultados atuais da verificação integrada. As suítes de integração
server/browser/jobs pertencem ao runner designado pelo Orchestrator e rodam após
a integração do candidato; falhas são corrigidas e os checks falhos ou afetados
são repetidos até todos passarem. Este prompt não inicia outra rodada de suítes
por causa da publicação. Reutilize evidências não afetadas e execute somente
checks adicionais exigidos por uma mudança relevante ou lacuna concreta. Use os
comandos dos manifests, regras e documentação atuais; não substitua comandos exatos por
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

- compare migrations, snapshots e metadados com o `main` do remote verificado;
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

Informe pré-requisitos, passos reproduzíveis, resultado observado e limites dos
caminhos felizes manuais exigidos pela Spec. Estados negativos, erro e recuperação
são cobertos por testes automatizados; não adicione jornadas manuais para publicar.
Quando não aplicável, diga explicitamente.

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

# Estratégia de Branches

## Branches principais

| Branch | Descrição |
|---|---|
| `production` | Código estável em produção. Nunca recebe commits diretos. |
| `main` | Branch de integração contínua (develop). Toda feat aprovada é mergeada aqui. |

---

## Fluxo de merge

```
branch de trabalho → main → production
```

Todo merge para `main` exige Pull Request com ao menos **uma aprovação**. O merge para `production` é feito apenas ao fim de cada sprint após validação do PO.

---

## Branches de trabalho

Todos os branches de trabalho são criados a partir de `main` e seguem o padrão:

```
<tipo>/<escopo>/<descricao-curta>
```

### Tipos

| Tipo | Quando usar |
|---|---|
| `feat` | Nova funcionalidade mapeada em uma User Story ou Task |
| `fix` | Correção de bug identificado em desenvolvimento ou QA |
| `hotfix` | Correção urgente aplicada diretamente sobre `production` |
| `chore` | Tarefas de infraestrutura, configuração, CI/CD, dependências |
| `refactor` | Refatoração de código sem alteração de comportamento |
| `docs` | Criação ou atualização de documentação |

### Escopo

O escopo identifica o repositório ou camada afetada: `server`, `mobile`, `iac`.

### Exemplos

```
feat/server/sign-in-endpoint
feat/mobile/petition-upload-ui
fix/server/signed-url-generation
chore/iac/gcp-staging-infra
docs/server/swagger-setup
refactor/server/applicability-calculation
```

Observe que os branches existentes no repositório já seguem esse padrão:

```
ANI-26-mobile-CI-typecheck-codecheck   →  chore/mobile/ci-setup
ANI-39-sign-in-screen                  →  feat/mobile/sign-in-screen
ANI-40-mobile-Tela-de-Sign-Up-Cadast   →  feat/mobile/sign-up-screen
ANI-41-google-auth-ui-mobile           →  feat/mobile/google-auth-ui
ANI-42-reset-password-screen           →  feat/mobile/reset-password-screen
ANI-43-create-profile-screen           →  feat/mobile/profile-screen
```

> O número do ticket Jira no início do nome é aceitável e facilita a rastreabilidade — mantenha esse padrão.

---

## Regras gerais

- Nunca commitar diretamente em `main` ou `production`
- Branches devem ser deletados após o merge
- Manter o branch atualizado com `main` antes de abrir o PR (`git rebase main` ou `git merge main`)
- Um branch por task — evitar branches que acumulam múltiplas feats
- Hotfixes são criados a partir de `production` e mergeados de volta em `production` **e** `main`
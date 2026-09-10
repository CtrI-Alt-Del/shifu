# Padrão de Commit

O projeto segue a convenção [Conventional Commits](https://www.conventionalcommits.org/).

## Estrutura

```
<tipo>: <ID-DO-TICKET> <descrição curta>

[corpo opcional]

[rodapé opcional]
```

O ID do ticket Jira é **obrigatório** e deve vir logo após os dois pontos, antes da descrição.

---

## Tipos

| Tipo | Quando usar |
|---|---|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `refactor` | Refatoração sem mudança de comportamento |
| `chore` | Tarefas de build, CI, configuração, dependências |
| `docs` | Criação ou atualização de documentação |
| `test` | Adição ou correção de testes |
| `style` | Formatação, espaçamento — sem mudança de lógica |
| `perf` | Melhoria de performance |
| `revert` | Reversão de commit anterior |

---

## Exemplos

```
feat: SHI-51 add analysis report pdf export flow

fix: SHI-61 correct signed url generation for petition upload

chore: SHI-22 add typecheck step to github actions pipeline

docs: SHI-51 update analysis exporting specification docs

refactor: SHI-52 extract applicability calculation to domain service

test: SHI-51 add coverage for analysis report export flow
```

---

## Regras

- O **ID do ticket Jira é obrigatório** e deve vir imediatamente após os dois pontos (`feat: SHI-51 ...`)
- A descrição deve estar em **inglês**, no **imperativo** e com **letra minúscula**
- Máximo de 72 caracteres na linha do título
- Não terminar o título com ponto final
- O corpo do commit deve explicar **o quê** e **por quê**, não o como
- Usar `BREAKING CHANGE:` no rodapé quando houver quebra de contrato
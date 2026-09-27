# SHIFU-68 — Autoridade visual para remoção de Habilidade

Este bundle congela as referências de `design/shifu.pen` usadas pela Spec da
SHIFU-68. As capturas foram exportadas em escala 1 em 2026-09-25 e inspecionadas
visualmente após a exportação. Nenhuma alteração foi feita no arquivo Pencil.
Em 2026-09-26, a SHIFU-66 foi confirmada como concluída e integrada ao `main`:
`uyfWq` e `wXPwI` agora correspondem à superfície produtiva
`SkillExperience`/`SkillOverview`, não a uma página provisória. O SHIFU-68 deve
preservar essa composição e substituir somente o gatilho inerte pelo menu real.

| Referência | Node Pencil | Superfície/estado | Viewport/exportação | Inventário visível | Uso na implementação | Validação |
| --- | --- | --- | --- | --- | --- | --- |
| [Confirmação](references/C51Tjy.png) | `C51Tjy`, `06.2 Habilidade · confirmar remoção` | Confirmação destrutiva aberta | Componente de 440 px, escala 1 | Ícone de lixeira, título com nome, explicação de isolamento, três grupos de perda, Cancelar e commit preenchido com `--danger` | Conteúdo e hierarquia do `ConfirmationDialog` | CA-08–CA-10, VM-01 |
| [Página desktop](references/uyfWq.png) | `uyfWq`, `10.4 Habilidade · menu aberto` | Página de Habilidade com menu disponível | 1440 × 900, escala 1 | Cabeçalho, nome/status da Habilidade, gatilho neutro e conteúdo da experiência SHIFU-66 | Posição do gatilho e preservação do restante da página | CA-08, CA-12, CA-13, VM-01 |
| [Página mobile](references/wXPwI.png) | `wXPwI`, `10.4 Habilidade · menu aberto · Mobile` | Página de Habilidade com menu aberto | 390 × 844, escala 1 | Navegação compacta, gatilho de ações, menu sem corte e conteúdo em coluna | Responsividade, foco e área acionável | CA-08, CA-13, VM-02 |
| [Menu](references/wr9RG.png) | `wr9RG`, `Skill actions dropdown open` | Menu de ações aberto | Componente de 228 px, escala 1 | Item único “Remover habilidade”, ícone e tratamento destrutivo sem preenchimento | Componente reutilizado em Habilidade, Lista e Grafo | CA-08–CA-11, CA-13, VM-01–VM-03 |

As composições de Lista e Grafo permanecem sob a autoridade já salva em
[`../../goal-details/design/manifest.md`](../../goal-details/design/manifest.md),
especialmente os frames `Eu1jl` e `HZQyi`. A SHIFU-68 substitui somente o stub
desabilitado de “Mais ações” por esse menu; não redesenha cartões, nós, relações,
controles de visualização ou layout do grafo.

## Decisões de handoff

- O gatilho destrutivo é neutro; somente o commit dentro da confirmação usa
  `--danger`, conforme `documentation/design.md` §3.3.
- A confirmação usa o nome real da Habilidade e a cópia do node `C51Tjy`.
  O aviso compartilhado de irreversibilidade pode permanecer como complemento
  textual exigido por RP-21, sem substituir a lista de perdas.
- A lista visual resume as perdas em três linhas. O backend continua obrigado a
  remover todo o inventário de RP-21: justificativa de inclusão, diagnóstico,
  evidências/bases por Conceito, progresso/domínio/cobertura/verificação por
  Competência, recomendação, conteúdo liberado, tentativas, avaliações e resumo
  final.
- Não há frame separado para pending ou erro. Esses estados suplementares seguem
  os componentes/tokens atuais: commit e cancelamento ficam indisponíveis durante
  a requisição; falha mantém a confirmação aberta com mensagem recuperável.
- As capturas exportadas estão íntegras, sem conteúdo colapsado, cortado ou
  sobreposto. Capturas frescas de runtime são obrigatórias na avaliação; estas
  referências não substituem a validação com Playwright CLI.

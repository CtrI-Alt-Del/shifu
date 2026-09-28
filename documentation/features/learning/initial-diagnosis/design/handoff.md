# Handoff visual — diagnóstico inicial

Fonte editável: `design/shifu.pen`, inspecionada pelo Pencil MCP em 2026-09-27.
As dez referências foram exportadas na escala 1, abertas individualmente e
conferidas visualmente. Cada PNG é válido, não vazio e mede 1440 × 900. A
inspeção estrutural dos dez quadros não encontrou descendentes cortados. As
capturas preservam estados ilustrativos; o Currículo é a fonte do enunciado,
linguagem de código, alternativas e ordem reais.

| Referência | Fonte/nó | Rota, superfície e estado | Viewport | Captura | Inventário visível | Interação e estado | Ambiguidades e exclusões | Validação |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Múltipla seleção | `design/shifu.pen` / `S4YpF1` | Atividade diagnóstica, seleção múltipla | 1440 × 900 | [S4YpF1](./references/S4YpF1.png) | Cabeçalho Diagnóstico, Competência e questão, barra de avanço, enunciado, trecho, quatro opções, Responder | Seleção reversível de várias opções e envio | O conteúdo Python é exemplo; não revelar se a seleção está correta | CA-03, CA-04, CA-06, VM-01, VM-02 |
| Escolha única | `design/shifu.pen` / `XhhBc` | Atividade diagnóstica, escolha única | 1440 × 900 | [XhhBc](./references/XhhBc.png) | Mesmo cabeçalho, trecho, opções com rádio, Responder | Uma opção por vez, sem retorno individual | Alternativa destacada indica seleção, não correção | CA-03, CA-04, CA-06, VM-01, VM-02 |
| Código inicial | `design/shifu.pen` / `WBynJ` | Atividade diagnóstica, ambiente iniciando | 1440 × 900 | [WBynJ](./references/WBynJ.png) | Editor com arquivo, números de linha, linguagem, terminal iniciando, Responder indisponível | Inicialização da prática sem nota | Nome `main.py` e Python 3 são dados ilustrativos do Currículo | CA-05, CA-15 |
| Código editado | `design/shifu.pen` / `ySy6z` | Atividade diagnóstica, edição e prática | 1440 × 900 | [ySy6z](./references/ySy6z.png) | Editor preenchido, terminal, Responder | Editar e enviar; prática automática | Saída de prática não determina avaliação oficial | CA-05, CA-06 |
| Atualizando saída | `design/shifu.pen` / `nKW30` | Atividade diagnóstica, prática atualizando | 1440 × 900 | [nKW30](./references/nKW30.png) | Editor realçado, indicador Atualizando saída, Responder indisponível | Estado transitório anunciado | Não confundir com avaliação oficial pendente | CA-05, CA-15 |
| Saída atualizada | `design/shifu.pen` / `TGtd8` | Atividade diagnóstica, prática concluída | 1440 × 900 | [TGtd8](./references/TGtd8.png) | Saída e tempo de prática, Responder | Envio disponível com resposta válida | Tempo e texto de saída são exemplos, não critérios de nota | CA-05 |
| Erro do código | `design/shifu.pen` / `R03lF9` | Atividade diagnóstica, erro de sintaxe na prática | 1440 × 900 | [R03lF9](./references/R03lF9.png) | Editor com borda de erro, mensagem com linha, Responder | Permitir corrigir e enviar; erro de prática não vira zero automático | Mensagem deve distinguir erro do código de falha do Shifu | CA-05, CA-07 |
| Falha de envio | `design/shifu.pen` / `IqIz3` | Atividade diagnóstica, envio falhou | 1440 × 900 | [IqIz3](./references/IqIz3.png) | Código preservado, alerta, Tentar novamente | Repetir envio com mesma resposta e chave idempotente | Falha de transporte não é avaliação nem nota | CA-07, CA-15 |
| Ponto de partida | `design/shifu.pen` / `Yn7tE` | `/learning/goals/$goalId/skills/$skillId/diagnostic/result`, aprendizagem | 1440 × 900 | [Yn7tE](./references/Yn7tE.png) | Título, síntese, Competências em ordem, valores, estimativa parcial, sem evidência, foco, bloqueio, ação recomendada | Ação abre Atividade oficial; resultado continua acessível | Números e nomes são exemplos; não expor itens diagnósticos | CA-10, CA-11, CA-13, VM-01, VM-02 |
| Conclusão direta | `design/shifu.pen` / `zaJXn` | Mesma rota, Habilidade concluída pelo diagnóstico | 1440 × 900 | [zaJXn](./references/zaJXn.png) | Título, texto sem evolução fictícia, quatro Competências dominadas, Ver resumo da Habilidade | Ação abre a página habitual da Habilidade | Os marcadores `Em foco` e `Bloqueada` no quadro são dados ilustrativos inconsistentes com quatro Competências dominadas; não reproduzi-los nesse estado | CA-12, CA-13 |

## Aplicação e tokens

O shell, fundo quadriculado, navegação, tipografia, cores, bordas e espaços
seguem `documentation/design.md` e os tokens já presentes no app. Os quadros
de Atividade mapeiam para `ActivityPage`, `ChoiceQuestion` e `CodeQuestion`;
o resultado mapeia para a nova `DiagnosticResultPage`. Não recriar o shell nem
introduzir um conjunto paralelo de tokens. A seleção deve ser identificável por
estado acessível e texto, não apenas pela borda vermelha; progresso, foco,
estimativa parcial e ausência de evidência também precisam de texto.

Os quadros não incluem uma versão mobile, confirmação de saída, avaliação
oficial pendente, falha da avaliação oficial ou execução invalidada por outra
aba. Capturas suplementares de design **não são necessárias**: a composição
responsiva e os estados funcionais são definidos pelo PRD, por
`documentation/design.md`, pelos widgets existentes e pela Spec.

## Revisão 8 — controle de avanço e envio final

Os botões “Responder” nos quadros de Atividade são referências visuais da
posição, dimensão e ênfase do controle, não de sua ação ou texto atual. O
pedido direto de envio único substitui o comportamento mostrado: o controle
avança como “Próxima questão” dentro da mesma Competência e “Próxima competência” na
transição entre Competências; somente a última questão da última Atividade
mostra “Enviar diagnóstico”. Nenhum desses avanços inicia avaliação oficial.
Após o envio final, a UI apresenta uma única espera agregada antes do resultado.
Manter os mesmos widgets `ActivityPage`, `ChoiceQuestion` e `CodeQuestion`,
hierarquia, tokens e estados de seleção/código dos quadros. A comparação
visual VM-01/VM-02 usa o controle com texto atualizado; a diferença de cópia
e ação é deliberada, aprovada pelo usuário.

Na revisão 8, a comparação visual exigida na entrega cobre somente o caminho
feliz: uma seleção
diagnóstica (`XhhBc` ou `S4YpF1`) e o resultado normal (`Yn7tE`): uma captura
fresca de cada superfície em 1440 × 900 na jornada persistida VM-01 e uma de
cada em 390 × 844 na checagem de layout/teclado VM-02. As demais
referências permanecem orientação de implementação, com estados e regras
verificados por testes automatizados; os casos negativos e desfechos alternativos
são verificados pelas suítes automatizadas, sem VM manual. VM-01 compara as
duas capturas desktop; VM-02 registra foco, corte e rolagem mobile. Qualquer
diferença material observada durante uma verificação executada deve ser
corrigida antes da conclusão.

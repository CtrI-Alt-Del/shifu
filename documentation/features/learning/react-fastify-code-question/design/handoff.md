# SHIFU-90 — referências e composição visual

Este é o inventário visual único de [spec.md](../spec.md), revisão 3. A revisão 3 altera isolamento da prévia e manutenção de testes, preservando estas referências. Referências exportadas pelo Pencil MCP e inspecionadas em 2026-10-25. O arquivo `design/shifu.pen` foi consultado somente por MCP. Nenhuma edição do documento foi feita.

## Estados e referências

| ID | Estado / superfície | Referência salva | Viewport de implementação | Critérios / verificação |
| --- | --- | --- | --- | --- |
| V-01 | Atividade integrada, aba Arquivos, frontend/API/adicional no explorador, prévia real e status local | [pcDeY.png](references/pcDeY.png), frame `pcDeY`, 1440×900 | 1440×900 | CA-02/03/04/06/13; VM-01/03 |
| V-02 | Atividade integrada, aba Enunciado, rubrica pública, editor e painéis de prática | [tDF6r.png](references/tDF6r.png), frame `tDF6r`, 1440×900 | 1440×900 | CA-03/04/08/13; VM-01/03 |
| V-03 | Como será avaliado com nomes/pesos curriculares | [xeppf.png](references/xeppf.png), recorte 248×211 | Dentro de V-02 | CA-08/13; VM-01/03 |
| V-04 | Editor e abas Prévia/HTTP/Terminal no mobile | Adaptação de V-01/V-02 e `documentation/design.md` `9; não existe frame mobile específico | 390×844 | CA-06/07/13; VM-02/04 |
| V-05 | Avaliação preliminar e resultado oficial com arquivos somente leitura | Composição existente de QuestionFeedback e ChoiceResultDetail; extensão integrada descrita na Spec | 1440×900 e 390×844 | CA-08/12/13; VM-01/04 |

A rota é a Atividade Learning existente, com parâmetros de Objetivo, Habilidade, Competência e Atividade. O resultado usa a rota existente da tentativa. Os IDs dos dados de runtime vêm da fixture descartável. Não fixar IDs do desenho ou do banco compartilhado.

O nome do frame `tDF6r` menciona HTTP. A imagem salva mostra a aba Prévia selecionada e HTTP/Terminal disponíveis. Ela não contém uma captura de resposta HTTP ou terminal. Esses estados usam a mesma composição, com os controles e resultados definidos no contrato. Não declarar uma referência inexistente.

## Composição e estado

- ActivityPage mantém cabeçalho, dificuldade, posição, progresso, respostas congeladas e ações de avaliação/envio.
- ReactFastifyQuestion possui arquivos atuais, seleção, criação de arquivo, estado de rascunho e assinatura do runner.
- ProjectPanel compõe o explorador e o editor existentes. Novo arquivo fica no explorador. O formulário local mostra a política curricular e valida nome/caminho antes de criar.
- PreviewPanel renderiza somente a URL/status validados pelo adapter, com iframe isolado.
- HttpPanel possui método, rota, corpo quando aplicável, resultado/erro e cancelamento do envio. Os exemplos curriculares preenchem campos sem enviar automaticamente.
- TerminalPanel usa xterm.js para saída e comandos permitidos. A entrada tem nome acessível e aceita comandos por correspondência exata, sem shell.
- QuestionFeedback e ChoiceResultDetail mostram a mesma resposta integrada congelada, com troca de arquivo somente leitura e rubrica completa. Não iniciam prática.

O botão primário da questão é Avaliar questão. Após avaliação conclusiva, manter Próxima questão ou Enviar atividade conforme posição. Inconclusão não mostra uma nota zero nem permite avançar.

## Mapeamento de tokens e primitivas

Valores verificados em `apps/web/src/ui/shared/styles/global.css`, `ui/shadcn/{button,input,tabs}.tsx` e nas regras UI/Design. Não introduzir outra paleta, fonte ou escala.

| Elemento | Token / primitiva existente | Aplicação |
| --- | --- | --- |
| Fundo da estação | `bg-background`, `bg-card`, `bg-surface-alt`, `bg-muted` | Separação entre página, editor, explorador e controles |
| Texto principal/de apoio | `text-foreground`, `text-secondary-foreground`, `text-muted-foreground` | Corpo, instruções e metadados |
| Rubrica pública | `bg-jade-tint`, `text-jade-text` | Caixa Como será avaliado e confirmação de salvamento |
| Ação principal | Button `variant='default'`, `bg-primary`, `text-primary-foreground` | Avaliar questão ou ação sequencial aplicável |
| Ações auxiliares | Button `variant='outline'` ou `'ghost'` | Novo arquivo, requisição HTTP e navegação secundária |
| Campos HTTP/arquivo | Input, Textarea e controles de seleção existentes | Borda `border-control-border` e foco da primitiva |
| Abas | Tabs, TabsList, TabsTrigger e TabsContent existentes | Enunciado/Arquivos e Prévia/HTTP/Terminal |
| Título editorial | `font-serif` | Enunciado ou título já pertencente à composição atual |
| Corpo e controles | `font-sans` | DM Sans |
| Código, nomes de arquivo e resultado numérico | `font-mono` | JetBrains Mono |
| Espaço | Escala Tailwind existente 1/2/3/4/6/8/12 | Equivale a 4/8/12/16/24/32/48; escolher pela composição existente |
| Raios | `rounded-md` nos controles existentes; demais superfícies seguem as classes da composição atual | Não criar valores arbitrários copiados do desenho |
| Limites de controles | `border-control-border` | Não usar divisor decorativo como única borda clicável |
| Foco | Tratamento existente da primitiva e regra de foco composto | Um indicador visível; campos compostos delegam o foco ao invólucro |
| Animação | MotionEntrance, ENTRANCE_* e AnimatedNumber atuais, quando a composição já os usar | Preferência reduzida mostra estado final sem atrasar informação |
| Erro e recuperação | Tokens `text-selo-text` e superfícies neutras atuais | Texto que atribui falha ao Shifu ou à prática; preservar trabalho |

A adaptação não requer mudar CSS global.

O Input atual já declara borda/foco. O novo widget não deve sobrepor outro anel. Se um invólucro possuir o foco, seguir integralmente a regra UI de foco composto. A revisão visual deve inspecionar o foco efetivo no navegador.

## Adaptações permitidas e preservação

1. **Novo arquivo:** `pcDeY` ainda contém botão na barra superior e um + simples no explorador. O ticket atualizado determina um único controle no explorador com ícone de arquivo com +. Implementar essa decisão explícita e remover a duplicação, sem editar a referência.
2. Nomes de arquivos, quantidade máxima, diretórios, extensões, textos da Atividade e percentuais 30/40/30 são exemplos visuais. A UI usa o conteúdo curricular efetivo.
3. O layout existente da página mantém seu contêiner externo `mx-auto w-full max-w-7xl` e gutters atuais. Não copiar medidas antigas que contrariem a regra UI.
4. Mobile empilha/reorganiza painéis por abas. Editor usa a largura disponível. Scroll horizontal fica no conteúdo de código quando necessário, não na página. Ações essenciais têm alvo de pelo menos 44 px.
5. HTTP/Terminal mantêm tipografia, superfícies e hierarquia da estação. Exibir método/rota/corpo, status/resposta e texto do terminal com rótulos, sem afirmar correspondência com uma captura inexistente.
6. Avaliação preliminar/oficial reutiliza a composição dos componentes atuais. A diferença é incluir todos os arquivos da resposta integrada e preservar somente leitura.
7. Shell, navegação, escolhas, JavaScript/React existentes e telas fora da Atividade/resultado não fazem parte da alteração visual.

Estados de loading, erro, armazenamento indisponível, prática incompatível, requisição cancelada e inconclusão pertencem à cobertura automatizada. Não criam jornadas manuais adicionais. Devem continuar claros, acessíveis e sem confundir falha com nota zero.

## Captura e comparação

Durante VM-01/02, salvar capturas sob `apps/web/.playwright-cli/screenshots/` com nomes que identifiquem SHIFU-90, estado e viewport. O resultado real fica em Evaluation durante a implementação. Não salvar evidência de runtime neste diretório de referências.

Inspecionar cada captura quanto a hierarquia, densidade, alinhamento, cores, fontes, foco, estados, overflow e disponibilidade das ações. Confirmar status e persistência por requests/banco nos checks correspondentes. As imagens não são prova desses efeitos.

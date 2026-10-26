# SHIFU-97 — referências e composição visual

Fonte editável: design/shifu.pen. Consulta e exportação pelo Pencil MCP em 25/10/2026. Os arquivos abaixo foram exportados em escala 1 e inspecionados visualmente. O documento Pencil não foi alterado.

## Inventário obrigatório

| ID | Superfície e estado | Viewport | Referência salva | Critérios | Verificação |
| --- | --- | --- | --- | --- | --- |
| D-01 | /account, Perfil carregado | 1440 × 900 | [Zhv5S.png](references/Zhv5S.png), nó Zhv5S | CA-02–CA-06, CA-12–CA-13 | VM-01 / VM-03 |
| D-02 | /account, Segurança carregada | 1440 × 900 | [w3b63H.png](references/w3b63H.png), nó w3b63H | CA-07–CA-08, CA-12 | VM-02 / VM-04 |
| D-03 | /account, Perfil carregado | 390 × 844 | Adaptação de D-01, sem quadro mobile próprio | CA-04, CA-12–CA-13 | VM-01 / VM-03 |
| D-04 | /account, Segurança carregada | 390 × 844 | Adaptação de D-02, sem quadro mobile próprio | CA-07, CA-12 | VM-02 / VM-04 |

A adaptação mobile é uma premissa visual aceita pela instrução do usuário de seguir todas as recomendações. Preserva ordem, hierarquia e controles. Usa uma coluna, margens laterais de 20 px, ações que podem ocupar a largura disponível e rolagem vertical. Não cria ações ou permissões novas. Capturas de execução pertencem a apps/web/.playwright-cli/screenshots/, nunca a esta pasta.

## Composição

- Preservar o shell autenticado existente, incluindo cabeçalho, navegação mobile, menu da conta, Mentor e saída.
- A página tem título editorial “Sua conta” e duas abas: Perfil e Segurança.
- Perfil contém o formulário de nome, e-mail somente leitura, fuso e Salvar. Abaixo fica o cartão “Seus dados e privacidade”.
- Segurança contém “Alterar senha”, senha atual, nova senha e a explicação “Os outros acessos serão encerrados. Este continua.” A confirmação posterior explica o resultado realizado.
- Cada formulário possui seu próprio hook de comportamento. O cartão de privacidade apenas apresenta links e texto. A página controla a aba e a carga do perfil.
- Não acrescentar campo de confirmação da nova senha, avatar, biografia, preferências de aprendizagem ou gestão de dispositivos.

## Tokens e primitivos verificados

| Elemento | Referência Pencil | Contrato Shifu |
| --- | --- | --- |
| Página | page, text-primary | bg-background, text-foreground; shell mx-auto w-full max-w-7xl; coluna interna até a largura editorial de 1150 px |
| Título | Instrument Serif, 36 px no quadro | font-serif; escala tipográfica existente, sem fonte paralela |
| Corpo, abas e controles | DM Sans | font-sans; text-sm e text-base conforme a hierarquia do quadro |
| Cartões | surface, radius-card | bg-card, border-border, rounded-lg/raio de cartão existente; sem sombra nova |
| Campos editáveis | raised, control-border, radius-control | Input compartilhado; bg-muted, border-control-border, rounded-md |
| E-mail | surface-alt, text-muted | Input readOnly com bg-surface-alt; rótulo “E-mail · não editável”; continua selecionável |
| Ação principal | selo-fill, on-selo | Button variant='default'; uma ação principal por formulário |
| Links de privacidade | contorno neutro | Anchor route='privacy'; Button variant='outline' quando composto como link; contato mailto nativo |
| Abas | superfície neutra e seleção contrastante | Tabs compartilhado; nomes acessíveis e navegação por setas |
| Fuso | V2/Input provisório | Select compartilhado sobre Base UI 1.8.0; valor IANA separado do rótulo pt-BR; opção selecionada legível também com a lista fechada |
| Foco | selo-text | Regra UI de um foco visível: border-ring e ring-2 ring-ring/20. Corrigir o Input compartilhado neste limite, sem sobrescritas de foco da página |
| Falha / sucesso | selo-text / jade-text | Texto e anúncio acessível, além da cor; pending exposto com aria-busy e botão indisponível |

O código já declara os tokens de cor e as famílias no CSS global. Espaçamento, raios, superfícies e foco devem usar os tokens existentes. O Select novo pertence à biblioteca compartilhada, sem cores ou escala próprias. Não recriar os componentes V2/Input e V2/Button como um segundo sistema.

## Desvios aceitos

- O quadro mostra “Excluir conta”. Essa aba é omitida porque SHIFU-97 exclui o fluxo e ele não existe na página atual.
- O cabeçalho e a navegação existentes prevalecem sobre a representação antiga do shell no quadro.
- O shell externo segue max-w-7xl, exigido pela regra UI. A largura editorial do quadro é uma restrição interna.
- Controles mobile possuem alvos de pelo menos 44 px. Textos e ações podem quebrar linha.
- O seletor de fuso substitui o campo provisório do Pencil. O fuso salvo tem prioridade. Sem valor salvo, a sugestão do navegador é identificada como ainda não salva.
- Dados fictícios das imagens são substituídos pelo perfil real. Nenhum offset GMT fixo é prometido, pois horário de verão pode mudar.
- A orientação e o endereço de privacidade vêm do contrato existente da SHIFU-96. Esta entrega não modifica o texto da política.
- A entrada usa MotionEntrance e variantes compartilhadas. Movimento reduzido mostra o estado final imediatamente.

Estados negativos, carregamento, falha, resultado incerto e recuperação pertencem à cobertura automatizada. Não exigem outros percursos manuais nem quadros estáticos novos.

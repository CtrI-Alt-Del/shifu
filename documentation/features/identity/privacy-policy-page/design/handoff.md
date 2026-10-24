# SHIFU-96 — handoff visual

## Superfícies e referências

| Superfície | Viewport | Referência | Critérios |
| --- | --- | --- | --- |
| Política pública desktop | 1440 × 2500 | [`w6IXZ.png`](references/w6IXZ.png), Pencil node `w6IXZ` | Cabeçalho de 80 px; container de até 1150 px; título editorial; índice de 240 px e coluna de leitura de 740 px; leitura sem overflow horizontal. |
| Política pública mobile | 390 × altura de rolagem | [`yJrRV.png`](references/yJrRV.png), Pencil node `yJrRV` | Padding lateral de 20 px; índice antes do texto; coluna fluida; links quebram sem overflow; leitura por teclado. |

As capturas foram exportadas do arquivo Pencil `design/shifu.pen` em 21/10/2026. O conteúdo visual nelas veio de rascunho baseado em versões antigas das fontes e não é autoridade para o texto público. Preservar somente estrutura, hierarquia, tipografia, espaçamento e tema escuro.

## Direção e tokens

- Fundo `--page` (`#0A0A0C`); texto principal `--text-primary` (`#F4F2EC`); texto de apoio `--text-secondary` (`#C4BFB6`); metadados `--text-muted` (`#9A958D`); divisores `--divider`.
- Título e marca em Instrument Serif; navegação, corpo e títulos de seção em DM Sans.
- Coluna longa de texto, sem cartões em volta de cada seção; usar divisores apenas como separação editorial.
- Links e foco seguem tokens/estados já existentes no Web; texto ativo deve manter contraste AA e foco visível.
- O índice desktop fica ao lado do conteúdo; em mobile ele vem antes do conteúdo e recebe separação inferior.

## Estados e fluxo

1. Abrir `/privacy` diretamente, sem sessão, no desktop e no mobile.
2. Seguir âncoras do índice por mouse e teclado; cada alvo tem título hierárquico e foco visível.
3. Ativar o contato de privacidade e conferir o URI `mailto:` sem alegar que o pedido foi enviado ou recebido.
4. Seguir links para `/privacy` a partir de Minha conta, Entrar e Criar conta.

## Desvios aceitos

- A rota canônica será `/privacy`, conforme SHIFU-96; o rascunho Pencil indica `/privacidade`.
- Todo texto do rascunho será substituído pelo conteúdo da revisão 1 do Spec. Isso inclui empresa controladora, bases, menores, cookies, IA/transferências, direitos, retenção e data.
- O modal de exclusão não existe no Web atual. Não será criado nesta entrega; a página pública continua acessível após o encerramento porque a rota não exige sessão.

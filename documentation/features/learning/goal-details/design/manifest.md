# SHIFU-64 — Referências e contrato visual

Fonte: `design/shifu.pen`, conectado e inspecionado pelo Pencil MCP em 2026-09-23. Exportação PNG scale=1. O design não foi editado. Estes arquivos são referências de implementação versionáveis, não evidências de que a aplicação já foi implementada.

## Inventário

| Frame | Arquivo | Viewport | Estado | Critérios |
| --- | --- | --- | --- | --- |
| HZQyi | [HZQyi.png](references/HZQyi.png) | 1440×900 | Grafo preenchido, desktop | CA-02/03/04/05/06/09 |
| Eu1jl | [Eu1jl.png](references/Eu1jl.png) | 1440×900 | Lista preenchida, desktop | CA-03/04/05/09 |
| dNtGs | [dNtGs.png](references/dNtGs.png) | 390×844 | Grafo mobile | CA-03/04/06/09 |
| uNYG9 | [uNYG9.png](references/uNYG9.png) | 1440×900 | Carregamento | CA-07 |
| f9ra1 | [f9ra1.png](references/f9ra1.png) | 1440×900 | Erro recuperável | CA-07 |
| KQvnQ | [KQvnQ.png](references/KQvnQ.png) | 1440×900 | Objetivo vazio | CA-02/08 |
| TmJTW | [TmJTW.png](references/TmJTW.png) | 1440×900 | Foco em linha da Lista | CA-09 |

Os dois prints fornecidos pelo usuário correspondem às composições de Grafo/Lista. Os PNGs acima foram exportados diretamente dos frames atuais, evitando dependência dos anexos temporários.

## Componentes de referência e mapeamento

- V0YFJi — V2/SkillTreeNode, referência base 252×104: nó com ícone, título, menu, status e barra condicional.
- UGHnP — V2/SkillRow, referência base 820×67: linha com nome, justificativa opcional, status e ações.
- h7fGzC — V2/Header; VtmmA — V2/GridBackground. Reutilizar shell/background atuais, sem construir outra navegação.
- ygtpy — V2/Button/Primary; usar primitive Button existente no código.
- A página usa Instrument Serif no título, DM Sans em conteúdo e controles; título 40 desktop/30 mobile observado nos frames. Tipografia/contraste precedem encaixe artificial em altura fixa.
- Superfície de grafo/lista mapeada ao token surface-alt #1D1E22, texto foreground #F4F2EC, ação primary #DC2F2F, descrição text-secondary #C4BFB6, learning jade-text #7BD3B6, barra jade-fill #2F8C72. Criar apenas tokens ausentes em global.css, preservando nomes/valores já usados.
- Espaçamentos da escala 4/8/12/16/24/32/48; card raio 10, control 6; bordas de controle control-border. Foco 2px Selo text com offset 2. Não adicionar sombras para simular hierarquia.
- Largura acompanha o AppLayout atual max-w-7xl com padding responsivo. Não alterar globalmente o shell para reproduzir os 80px laterais do frame. Registrar a diferença de shell na comparação; conteúdo da feature mantém a hierarquia e proporções.

## Divergências resolvidas pelo contrato

| Evidência | Tratamento na implementação | Motivo |
| --- | --- | --- |
| design.md T12/mobile diz Lista inicial | Grafo inicial em qualquer viewport | PRD Learning v13 RP-04 e usuário |
| Desktop mostra ações de remoção/menu ativas | Mesmos componentes, disabled real, com explicação acessível | Usuário aprovou preparação visual, sem mutação |
| Mobile não mostra Remover objetivo | Preservar controle disabled também no cabeçalho responsivo, sem overflow | Decisão do usuário; adaptação explícita, não cópia exata |
| Mobile parece encadear todas as skills linearmente | Preservar A→C/B→C do dado; layout vertical não pode inventar A→B | Curriculum/PRD governam relações |
| Mobile não desenha controles de zoom | Incluir +/- e percentual acessíveis no canvas | Critério Jira exige zoom e uso mobile |
| Barra vazia na skill não iniciada do Grafo | Não renderizar barra/trilho em not-started, diagnosing ou completed | Critério explícito SHIFU-64 |
| Diagnóstico amarelo/latão | Neutro + ícone de busca + texto Em diagnóstico | design.md reserva latão à gamificação |
| TmJTW indica Grafo selecionado ao mostrar linha | Lista selecionada enquanto Lista é exibida | Coerência semântica e abas controladas |
| Foco de TmJTW pouco evidente | Anel de foco canônico e perceptível | Acessibilidade e design.md |
| Loading/erro usam título exemplo já preenchido | Skeleton ou título genérico sem dados; título real só depois de resposta autorizada | Resposta única e privacidade |
| Mobile abrevia título do Objetivo | Quebrar texto real e preservar nome completo acessível | Não inventar resumo de conteúdo do usuário |
| Sidebar do texto antigo difere do header atual | Reutilizar AppLayout existente | Fora do escopo reconstruir shell |

Esses ajustes não alteram o documento Pencil nem autoridades globais. São aplicação do comportamento aprovado e dos tokens/regras existentes ao recorte desta task. Registrar comparação como “fiel com diferenças contratuais”, nunca alegar pixel-perfect integral.

## Estados suplementares e captura futura

Não existem mockups dedicados confirmados para os cenários abaixo. Não inventar nomes de frames. As referências derivadas indicam composição; a Spec fixa comportamento e os testes fornecem evidência. Capturas runtime obrigatórias após implementação:

| Cenário | Viewport | Referência de composição | Decisão |
| --- | --- | --- | --- |
| Lista mobile | 390×844 | Eu1jl + dNtGs | Empilhar mantendo nome/status/link/menu; sem truncar informação essencial |
| Loading mobile | 390×844 | uNYG9 + dNtGs | Skeletons ajustados, texto anunciado |
| Erro mobile | 390×844 | f9ra1 + dNtGs | Texto e retry acessíveis |
| Vazio mobile | 390×844 | KQvnQ + dNtGs | Ação disponível sem overflow |
| Ausência privada desktop | 1440×900 | f9ra1 | “Objetivo não encontrado” + link Home, sem dados |
| Ausência privada mobile | 390×844 | f9ra1 + dNtGs | Mesmo conteúdo seguro |
| Quatro estados na Lista | 1440×900 | Eu1jl | Completed: check+Concluída, sem barra |
| Quatro estados no Grafo | 1440×900 | HZQyi | Mesmo status e navegação; sem progresso de completed |
| Foco no Grafo | 1440×900 | HZQyi + TmJTW | Link do nó e zoom com foco visível |
| Foco mobile | 390×844 | dNtGs + TmJTW | Keyboard e alvos mínimos 44px |
| Ações disabled desktop | 1440×900 | HZQyi/Eu1jl | Comportamento inerte, não apenas opacidade |
| Ações disabled mobile | 390×844 | dNtGs | Remover objetivo e menus sem colidir com nomes |
| Skill desconectada e duas bases | 1440×900 | HZQyi | Sem sobreposição ou arestas inventadas |
| Skill desconectada e duas bases mobile | 390×844 | dNtGs | Preservar topologia; pan/zoom não prende scroll da página |
| Erro de layout | 1440×900 | f9ra1 | Retry local, Lista ainda disponível |
| Título/descrição longos | 390×844 | dNtGs | Quebra natural; canvas e toolbar cabem na página |

Cada linha e cada frame original deve ter captura nova por Playwright CLI e resultado registrado na Evaluation. Pode reutilizar uma captura entre critérios quando ela realmente demonstra o mesmo estado/viewport; não usar um screenshot desktop como prova de mobile. Capturas runtime são temporárias, não versionar automaticamente.

## Texto e acessibilidade

- Abas: Grafo / Lista; aria-selected e tabpanel associados. Setas/Home/End, Tab para sair do grupo.
- Barra learning: nome acessível “Progresso de <Habilidade>”, mínimo 0, máximo 100 e valor atual; texto acessível do número, mesmo se visualmente discreto.
- Não iniciada: círculo tracejado + texto; Em diagnóstico: busca + texto; Em aprendizado: círculo + texto; Concluída: check + texto.
- Zoom: “Ampliar grafo”, “Reduzir grafo”; indicar percentual real. Desabilitar no limite.
- Remover objetivo: Button disabled; menu: “Mais ações de <Habilidade>”, disabled. Texto de apoio comunica disponibilidade futura.
- Erro de consulta: “Não foi possível carregar este objetivo” e “Tentar novamente”; sem stack, detalhes de banco ou token.
- Vazio: “Este objetivo ainda não tem habilidades” e “Adicionar Habilidade”.
- Skeleton e região de loading com status/busy; erros comunicados por região acessível sem roubar foco repetidamente.
- Preservar reduced-motion. Não exigir gestos exclusivos, cor ou posição para identificar ou acessar uma skill.


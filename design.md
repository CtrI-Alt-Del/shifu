# Shifu — Design System e Especificação de Telas

Documento base para a construção do design da aplicação no Pencil (pen.dev).

Fonte de verdade: os PRDs de **Identity**, **Curriculum**, **Learning**, **Intelligence** e **Gamification** publicados no Confluence do espaço Shifu. Toda regra de comportamento citada aqui vem de um PRD. Quando este documento propõe algo que os PRDs não definem, isso é decisão de design deste documento e pode ser alterado pelo time sem contrariar requisito.

A direção de marca está fechada na seção 3: **Dojo**, derivada da direção de arte do jogo Sifu, com três matizes de papel fixo e contraste verificado.

---

## 1. Escopo do design

### 1.1 O que existe no MVP

| Área | O que o usuário vê |
|---|---|
| Identity | Cadastro, confirmação de e-mail, entrada, recuperação e alteração de senha, perfil, sessões, exclusão de conta |
| Learning | Objetivos, Habilidades, diagnóstico, materiais, Atividades, avaliações, progresso, histórico, resumo final |
| Intelligence | Mentor (chat contextual) e Planejador de Objetivos (entrevista + proposta), cota mensal de IA |
| Gamification | XP, nível, sequência, conquistas, calendário de atividade, histórico de recompensas |
| Curriculum | Nenhuma tela própria. O Currículo é conteúdo consumido por Learning e Intelligence |

### 1.2 O que NÃO deve ser desenhado

Não criar telas para nada abaixo. Todos são exclusões explícitas dos PRDs.

- Área administrativa de Currículo (criar/editar Habilidade, Competência, material, Atividade)
- Login social, troca de e-mail, 2FA, lista de dispositivos, reativação de conta
- Ranking, perfis públicos, comparação entre usuários, compartilhamento de conversas
- Avatar, biografia, nome de usuário público
- Progresso ou conclusão do **Objetivo** (o Objetivo não tem nota nem barra de progresso próprios)
- Modo "prática" separado de modo "avaliação"
- Marcar material como lido / percentual de leitura / biblioteca geral de materiais
- Desafio final obrigatório após dominar todas as Competências
- Rascunho de resposta não enviada
- Configuração de IA pelo usuário (modelo, chave, parâmetros)
- Exportação de dados ou de conversas
- Painel de métricas / analytics
- Seletor de idioma. O MVP é somente pt-BR

---

## 2. Princípios de design

Cinco princípios que resolvem quase toda dúvida de layout. Eles saem direto dos PRDs.

**P1. Aprendizagem e gamificação nunca se misturam visualmente.**
Progresso, domínio e nota medem aprendizagem. XP, nível, sequência e conquistas medem engajamento. Os dois nunca compartilham o mesmo card, a mesma barra ou a mesma cor. O retorno de recompensa aparece separado do resultado pedagógico. Nível de Gamification jamais é apresentado como nível de conhecimento.

**P2. A IA orienta, não resolve e não decide.**
O Mentor sugere, explica e dá dicas progressivas. Ele nunca tem botão que altera estado: não cria Objetivo, não envia tentativa, não concede XP. Toda ação que muda dados fica na interface de Learning, acionada pelo usuário.

**P3. Nada essencial é comunicado só por cor.**
Exigido por Identity RP-10, Learning RP-25, Intelligence RP-12 e Gamification RP-06. Toda situação de Competência, dia do calendário, estado de avaliação e nível de cota carrega **ícone + rótulo textual**, não apenas cor. A cor é reforço.

**P4. Estados intermediários são de primeira classe.**
"Avaliação em andamento", "avaliação que não pôde terminar", "resposta sendo produzida", "conta aguardando confirmação", "planejamento bloqueado por cota" são telas com desenho próprio, não spinners genéricos. Regra dura de Learning RP-13: **nota zero significa desempenho zero, nunca "aguardando"**. Nunca usar o mesmo componente para os dois.

**P5. Privacidade nas mensagens de conta.**
Cadastro, entrada, reenvio de confirmação e recuperação de senha nunca revelam se um e-mail tem conta, se está ativa ou pendente. As mensagens de erro são genéricas por requisito, e o design não pode "ajudar" sendo específico.

---

## 3. Design tokens

Direção de marca: **Dojo**, derivada da direção de arte do jogo Sifu. Fundo quase preto, três matizes com papéis fixos, cantos duros, display condensado em caixa alta.

O produto é **dark only** no MVP. Nenhum PRD pede tema claro, e manter um só tema evita dobrar o custo de verificação de contraste.

### 3.1 A regra das três matizes

O sistema tem exatamente três cores. Cada uma tem um papel e não empresta esse papel para nenhuma outra função.

| Matiz | Papel | Onde aparece |
|---|---|---|
| **Jade** | Aprendizagem | Progresso, domínio, situação da Competência, sucesso |
| **Selo** | Ação, marca e erro | Botão primário, Competência em foco, logotipo, falha |
| **Latão** | Gamificação | XP, nível, sequência, conquistas, calendário |

Estados que não sejam sucesso ou erro usam **neutro mais ícone**, nunca uma quarta matiz. Aviso de cota, avaliação pausada e conteúdo bloqueado são neutros. Isso é deliberado: inflacionar matizes é o que faz um sistema perder significado.

Consequência direta do princípio P1: como latão nunca toca em nada pedagógico e jade nunca toca em recompensa, a separação entre aprendizagem e engajamento acontece sozinha, sem depender de disciplina de layout.

### 3.2 Cor

**Neutros**
```
--page              #121316   fundo da aplicação
--surface           #1E2025   cartões, listas
--raised            #262930   trilho de barra, campo, estado hover
--divider           #333740   linha decorativa, sem exigência de contraste
--control-border    #737A87   borda de campo, caixa, controle  [3,77:1]
--text-disabled     #6E747F   apenas desabilitado
--text-muted        #9AA0AB   metadado, legenda              [6,20:1]
--text-secondary    #C4C9D1   texto de apoio                 [9,80:1]
--text-primary      #F2F0EA   texto principal, branco quente [14,30:1]
```

**Jade — aprendizagem**
```
--jade-tint         #0C2A24   fundo de selo
--jade-fill         #2F8C72   preenchimento de barra
--jade-solid        #45A98B   barra concluída, ícone         [5,67:1]
--jade-text         #6FC7AA   texto sobre escuro             [8,09:1]
--on-jade           #121316   texto sobre jade-solid         [6,46:1]
```

**Selo — ação, marca e erro**
```
--selo-tint         #3A1210   fundo de selo
--selo-fill         #C63A2E   botão primário, marca
--selo-text         #E8877B   texto de erro, anel de foco    [6,35:1]
--on-selo           #FFFFFF   texto sobre selo-fill          [5,19:1]
```

**Latão — gamificação**
```
--latao-tint        #3A2C10   fundo de selo, borda de cartão
--latao-fill        #C08A22   preenchimento
--latao-solid       #DCA845   número de XP, nível, sequência [7,55:1]
--latao-text        #EFC877   texto sobre escuro            [10,24:1]
--on-latao          #121316   texto sobre latao-solid        [8,61:1]
```

Todos os valores entre colchetes são razões de contraste medidas contra `--surface`, exceto `--on-*`, medidas contra o próprio preenchimento. Todas passam em AA para texto normal. `--divider` fica abaixo de 3:1 de propósito: é ornamento, não delimita controle. Onde a borda delimita um controle, usar `--control-border`.

### 3.3 Como resolver ação destrutiva

Selo é a cor de ação primária. Se ação destrutiva também fosse selo preenchido, o usuário não distinguiria continuar de apagar. A regra:

- **Só a ação primária usa selo preenchido.** Uma por tela.
- **Destrutiva nunca é preenchida.** Superfície neutra, rótulo em `--selo-text`, borda em `--selo-text`, e sempre com ícone.
- **Destrutiva sempre vive dentro de confirmação.** Os PRDs já exigem isso em excluir conta, remover Objetivo e remover Habilidade, então a regra não custa nada.

### 3.4 Tipografia

Par de display condensado com sans neutra, o padrão observado em boot.dev, MasterClass e Brilliant.

- **Display:** Oswald, 600, caixa alta, entreletra +1,2. Só em logotipo, título de tela e etiqueta de seção.
- **Interface:** Inter. Todo o resto.
- **Numérico e código:** JetBrains Mono. Nota, progresso, XP, nível, sequência, editor.

Todas do Google Fonts, sem custo de licença.

| Papel | Família | Tamanho / Altura | Peso |
|---|---|---|---|
| Logotipo | Oswald | 26 / 32 | 600 |
| Título de tela | Oswald | 15 / 20 | 600 |
| Etiqueta de seção | Oswald | 11 / 16 | 600 |
| Título 1 | Inter | 24 / 32 | 600 |
| Título 2 | Inter | 18 / 26 | 600 |
| Corpo | Inter | 14 / 22 | 400 |
| Corpo forte | Inter | 14 / 22 | 500 |
| Pequeno | Inter | 13 / 20 | 400 |
| Legenda | Inter | 11 / 16 | 500 |
| Numérico | JetBrains Mono | 20 / 26 | 600 |
| Código | JetBrains Mono | 13 / 21 | 400 |

Material de apoio é exceção: Inter 16 / 28, largura máxima de 68 caracteres.

**Caractere chinês.** 師父 aparece **apenas no logotipo**, em `--selo-fill`, ao lado do nome. Não usar caracteres como ornamento em cabeçalho de seção. O nome do produto já é uma palavra chinesa, então na marca ele é significado; espalhado pela interface vira figurino. Se usados, manter tradicional, nunca misturar com simplificado.

### 3.5 Espaçamento, raio, elevação

```
Espaço    4  8  12  16  24  32  48
Raio      none 0    controle e cartão 2    modal 4
          A barra de progresso é retangular, raio 0. É um medidor, não uma pílula.
          Nada no sistema usa pill.
Borda     1px, sempre. Sem borda de 2px, exceto a marca de foco da Competência.
Elevação  Sem sombra. Hierarquia por superfície: page, surface, raised.
Foco      Anel de 2px em --selo-text com deslocamento de 2px.
```

O raio duro é a decisão de marca mais visível depois da cor. É o que separa isto de um template. Não relaxar para 8 ou 12 no meio do caminho.

### 3.6 Breakpoints e shell

```
mobile   < 640
tablet   640 a 1023
desktop  >= 1024
```

**Desktop:** trilho lateral fixo de 52px, só ícones, com 師 no topo. Conteúdo com largura máxima de 1120px.
**Mobile:** barra inferior com 4 itens — Objetivos, Progresso, Mentor, Conta.

O Mentor é painel lateral de 400px no desktop e folha em tela cheia no mobile. Abre de qualquer área, conforme Intelligence RP-04.

## 4. Biblioteca de componentes

Componentes a montar no Pencil antes das telas.

### 4.1 Base
Botão (primário, secundário, texto, destrutivo × tamanhos M/L × estados normal, hover, foco, pressionado, carregando, desabilitado) · Campo de texto · Campo de senha com mostrar/ocultar · Área de texto · Rádio · Caixa de seleção · Seletor · Alternador de abas · Divisor · Etiqueta · Selo · Dica de contexto · Avatar de iniciais.

### 4.2 Feedback
Alerta em linha (info, sucesso, aviso, erro) · Aviso de topo de página · Notificação flutuante · Modal de confirmação · Modal destrutivo (exige digitar senha) · Esqueleto de carregamento · Estado vazio (ícone + frase + ação) · Estado de erro recuperável (frase + **Tentar novamente**).

### 4.3 Aprendizagem
- **Cartão de Objetivo** — título, descrição truncada em 2 linhas, contagem de Habilidades por situação, menu de ações
- **Cartão de Habilidade** — nome, selo de situação (não iniciada / em diagnóstico / em aprendizado / concluída), ação principal contextual
- **Linha de Competência** — ordem, nome, barra de progresso, valor 0 a 100, selo de situação, marcador de foco, cadeado quando bloqueada
- **Barra de progresso da Competência** — com marcas visíveis em 40, 70 e 85
- **Cartão de próxima Atividade** — dificuldade, tipo, motivo (nova ou reforço), botão Iniciar
- **Selo de dificuldade** — Fácil / Média / Difícil, com forma distinta além da cor
- **Grafo de Habilidades** — nós = Habilidades do Objetivo, arestas = relações do Currículo. **Precisa de uma visão em lista equivalente** (Learning RP-25: o grafo não pode ser a única forma de descobrir nomes e caminhos)
- **Editor de código** — mono, numeração de linhas, botão Enviar. Sem execução local
- **Cartão de caso de teste** — entrada, esperado, obtido, aprovado/reprovado
- **Cartão de critério qualitativo** — nome, peso, nota 0 a 100, explicação curta
- **Linha de histórico de tentativa** — data, nota, expansível para resposta + avaliação

### 4.4 Gamification
- **Resumo compacto** — nível, XP total, sequência atual. Fica no shell e abre a área completa
- **Anel de nível** — nível atual, XP acumulado, XP faltando para o próximo
- **Chama de sequência** — valor atual + recorde histórico
- **Medalha de conquista** — obtida (com data) / bloqueada (com critério e progresso até o marco) / histórica (retirada do catálogo, visível só para quem obteve)
- **Célula do calendário** — cinco estados, cada um com forma própria
- **Linha do histórico de XP** — quantidade, data de concessão, origem legível

### 4.5 Intelligence
- **Bolha de mensagem** — usuário / mentor, com bloco de código formatado
- **Marcador de consulta** — mostra que o Shifu foi consultado, **sem expor o que foi consultado**
- **Barra de resposta em andamento** — texto aparecendo progressivamente + botão Cancelar
- **Medidor de cota** — percentual utilizado + data de renovação. Estados: normal, aviso em 80%, bloqueio em 100%
- **Cartão de pergunta do Planejador** — enunciado, alternativas (escolha única ou múltipla), opção "Não sei" quando fizer sentido. **Nunca campo livre e nunca opção "Outro"**
- **Trilha de etapas do lote** — qual etapa está atual e quais já foram respondidas, de forma acessível
- **Cartão da proposta** — título e descrição editáveis, lista de Habilidades com justificativa somente leitura

---

## 5. Mapa de telas

```
Público
  Cadastro
  Entrar
  Esqueci minha senha
  Redefinir senha
  Confirmar e-mail  (retorno do link)

Conta pendente  (acesso restrito)
  Aguardando confirmacao

Autenticado
  Home / Objetivos
    Criar Objetivo manual
    Planejamento assistido
      Lote de perguntas
      Proposta final
      Objetivo nao suportado
    Objetivo
      Adicionar Habilidade
      Habilidade
        Diagnostico
        Resultado do diagnostico
        Aprendizado
          Competencia
          Material de apoio
          Atividade  (escolha unica | codigo)
          Resultado da avaliacao
          Historico de tentativas
        Habilidade concluida
  Progresso  (Gamification)
    Calendario
    Conquistas
    Historico de XP
  Mentor  (painel, abre de qualquer tela)
    Lista de conversas
    Conversa
  Conta
    Perfil
    Seguranca
    Excluir conta
```

---

## 6. Especificação das telas

### 6.1 Identity

#### T01 — Cadastro
Campos: nome de exibição, e-mail, senha. Mínimo de 8 caracteres **declarado antes do envio**, não só no erro.
Erro de validação **não apaga** os campos já preenchidos corretamente.
Se o e-mail já estiver em uso, a mensagem preserva a privacidade e oferece três caminhos: entrar, recuperar senha, reenviar confirmação. Ela **não diz** se a conta é ativa ou pendente.
Sucesso leva para T02, nunca para área protegida.

#### T02 — Aguardando confirmação
Explica que o restante do produto está indisponível até a confirmação.
Botão **Reenviar link** com contador regressivo de 60 segundos quando ainda não for permitido.
Falha de envio mostra erro recuperável. O desenho não pode sugerir "cadastre-se de novo".

#### T03 — Retorno do link de confirmação
Quatro estados distintos, cada um com desenho próprio: **válido** (conta ativada), **expirado**, **já utilizado**, **inválido**. Os três últimos oferecem caminho de recuperação.
Se o usuário estiver no mesmo acesso iniciado pelo cadastro, segue para a Home. Caso contrário, vai para T04.

#### T04 — Entrar
E-mail e senha. Credencial inválida gera **uma única mensagem genérica**, sem revelar qual campo falhou.
Link para T05.
Conta ainda não confirmada entra com acesso restrito e cai em T02.

#### T05 — Esqueci minha senha
Um campo de e-mail. A resposta é genérica **sempre**, exista conta elegível ou não.
Reenvio respeita 60 segundos.

#### T06 — Redefinir senha
Distinguir link **válido**, **expirado**, **já utilizado** e **inválido**.
Nova senha com mínimo de 8 caracteres.
Após o sucesso: confirma a alteração, avisa que **todos os acessos foram encerrados** e direciona para T04. Se o e-mail ainda não estiver confirmado, deixa claro que essa etapa continua necessária.

#### T07 — Conta / Perfil
Nome de exibição editável, sem exigir senha.
E-mail visível e explicitamente **não editável**.
Fuso horário aparece aqui (Identity RP-06). A forma de escolha ainda não está definida no PRD — **decisão pendente do time**, desenhar como seletor e marcar como provisório.

#### T08 — Conta / Segurança
Alterar senha (senha atual + nova). Diferenciar visualmente erro de senha atual e erro de validação da nova.
Após o sucesso: informa que **os outros acessos foram encerrados e o atual permanece ativo**.
Ação **Sair de todos os dispositivos**, com aviso de que o acesso atual também termina.

#### T09 — Excluir conta
Modal destrutivo. Exige senha atual + confirmação explícita.
Texto deixa claro que é **definitivo, sem reativação**, e que atinge os dados em Learning, Intelligence e Gamification.
Estado **em andamento** com desenho próprio: enquanto a exclusão não terminar em todas as áreas, a interface **não pode comunicar conclusão**.
Falha aparece como erro recuperável com nova tentativa.

---

### 6.2 Home e Objetivos

#### T10 — Home
Ordem vertical exigida por Intelligence RP-07:
1. Campo de texto livre — criação assistida
2. Ação explícita de **criação manual**
3. Lista dos Objetivos existentes

A diferença entre assistida e manual precisa ser clara no próprio rótulo.
Se a cota estiver em 100%, o campo assistido aparece bloqueado com explicação e **a criação manual continua visível e utilizável**.
Estado vazio: nenhum Objetivo ainda, com as duas entradas em destaque.

#### T11 — Criar Objetivo manual
Título e descrição, ambos obrigatórios e marcados como tal.
Um Objetivo pode ser criado vazio e permanecer vazio.

#### T12 — Objetivo
Cabeçalho: título e descrição, editáveis a qualquer momento. **Sem barra de progresso e sem selo de conclusão** — o Objetivo não tem progresso próprio.
Corpo: as Habilidades do Objetivo, cada uma com sua própria situação.
Duas visões alternáveis: **lista** (padrão) e **grafo**. Só aparecem no grafo as Habilidades incluídas naquele Objetivo, e uma aresta só existe quando as duas pontas estão no Objetivo. Nada de nós intermediários ou ocultos.
Habilidades vindas do Planejador exibem a **justificativa de inclusão**, somente leitura.
Estado vazio: ação para adicionar Habilidade.
Menu: editar, remover Objetivo.

#### T13 — Adicionar Habilidade
Catálogo de Habilidades do Currículo com busca.
Habilidade já presente no Objetivo **não cria outra** — a interface leva para a experiência existente.
Adicionar **não inicia** o diagnóstico.
Relações do Currículo não bloqueiam nada e não podem aparecer como pré-requisito.

#### T14 — Remover Habilidade / Remover Objetivo
Dois modais destrutivos distintos.
Remover Habilidade: lista o que será perdido — diagnóstico, progresso, domínio, conteúdo liberado, tentativas, avaliações, justificativa e resumo final. Permitida em qualquer etapa, inclusive com avaliação pendente.
Remover Objetivo: deixa claro que **todas** as experiências de Habilidade dele serão removidas.
Remover a última Habilidade **não** remove o Objetivo. São ações diferentes.

---

### 6.3 Planejador de Objetivos

#### T15 — Lote de perguntas
Página separada, aberta a partir do campo livre da Home.
**Uma pergunta por etapa**, com navegação livre entre as perguntas do lote atual.
Formatos: escolha única e múltipla escolha. **Nunca** campo de texto livre, **nunca** opção "Outro". Pode existir "Não sei" quando fizer sentido.
Todas as perguntas do lote precisam de resposta antes do envio. O último passo tem ação clara **Enviar respostas**.
Lotes anteriores somem da interface.
A interface **não sugere quantos lotes ainda existirão** — nada de "etapa 2 de 4" entre lotes. A trilha de etapas vale só dentro do lote atual.
Quando o Planejador consultar o Currículo, mostrar que houve consulta, sem expor detalhes.
Ação de cancelar e voltar à Home sempre visível.

#### T16 — Proposta final
Tela única com o plano inteiro.
Título e descrição **editáveis direto**. Habilidades e justificativas **somente leitura**.
Três ações: **Ajustar** (campo livre descrevendo a mudança), **Confirmar**, **Cancelar**.
Não há volta para os lotes anteriores. Ajustar é o mecanismo de refinamento.
Propostas inválidas nunca chegam nesta tela — a correção automática acontece antes, invisível ao usuário.
Falha ao criar o Objetivo **não pode parecer sucesso parcial**: a proposta continua na tela para nova tentativa.

#### T17 — Objetivo não suportado
Mensagem clara de que nenhuma combinação de Habilidades existentes representa a intenção.
**Nenhuma Habilidade inventada aparece.**
Dois caminhos: reformular a intenção ou ir para a criação manual.

---

### 6.4 Learning

#### T18 — Habilidade não iniciada
Nome, descrição, quantidade de Competências.
Ação única: **Iniciar Habilidade**, que começa o diagnóstico.
Deixar claro que o diagnóstico percorre todas as Competências.

#### T19 — Diagnóstico em andamento
Mostra a Competência atual e o avanço geral.
**Não mostra** nota, correção, casos de avaliação nem retorno de IA de item algum.
Material de apoio, dicas e Mentor ficam **indisponíveis para a Atividade diagnóstica atual**. O Mentor continua acessível para outros assuntos — desenhar esse bloqueio como mensagem dentro do Mentor, não removendo o botão.
Uma resposta válida por Atividade. Sem rascunho.
Ao sair e voltar, retoma no próximo item não resolvido. Itens já avaliados permanecem concluídos.

#### T20 — Resultado do diagnóstico
Aparece só no fim do diagnóstico inteiro.
Lista consolidada por Competência: progresso inicial 0 a 100 e situação.
**Não expõe** respostas individuais, correções ou casos.
Se todas as Competências estiverem dominadas, a Habilidade é concluída direto e o resumo **não pode alegar evolução** — inicial e final são iguais.
Caso contrário, mostra qual é a Competência em foco e leva para T21.

#### T21 — Habilidade em aprendizado
A tela central do produto. Três blocos:

**a) Cabeçalho** — nome da Habilidade, nota geral (média dos progressos atuais de **todas** as Competências, inclusive as bloqueadas), selo de situação.

**b) Próxima Atividade recomendada** — em destaque. Mostra dificuldade e se é Atividade nova ou **reforço**. A dificuldade segue o progresso da Competência em foco: abaixo de 40 → fácil, de 40 a 69 → média, 70 ou mais sem domínio → difícil.
A recomendação **orienta, não obriga**. O usuário pode abrir qualquer Atividade de qualquer Competência liberada.
Nada começa automaticamente depois de uma avaliação.

**c) Lista de Competências** — na ordem do Currículo, cada uma com: número de ordem, nome, barra de progresso com marcas em 40/70/85, valor numérico, selo de situação, marcador de **foco** e cadeado quando bloqueada.
A Competência em foco é sempre a primeira ainda não dominada.
Conteúdo já liberado **nunca volta a ser bloqueado**, mesmo com queda de desempenho. Se o foco voltar para uma Competência anterior, a interface explica a mudança sem esconder o que já foi liberado.

Se existir avaliação pendente ou com falha nesta Habilidade, um aviso de topo explica que **apenas novas tentativas desta Habilidade estão pausadas** e que outras Habilidades seguem normais.

#### T22 — Competência
Materiais e Atividades **na ordem definida pelo Currículo**. Learning não reordena.
Dentro de uma Competência liberada, tudo abre imediatamente.
Ler material **não é pré-requisito** e **não altera progresso**. Nada de caixa "marcar como lido" ou percentual de leitura.
Competência bloqueada mostra claramente qual é.

#### T23 — Material de apoio
Leitura confortável, largura máxima de 68 caracteres.
Caminho de volta claro para a Competência de origem — o mesmo material pode aparecer em mais de uma Competência.

#### T24 — Atividade de escolha única
Enunciado + alternativas. Uma correta. Sem crédito parcial.
Aviso ao tentar sair com resposta não enviada: **o conteúdo será perdido** (não existe rascunho).
Após o envio, a avaliação começa sozinha. **Não existe segundo botão "avaliar"**.

#### T25 — Atividade de código
Enunciado + editor mono. Botão **Enviar**.
Os casos de avaliação ficam ocultos antes do primeiro resultado.
Mesmo aviso de perda de resposta não enviada.

#### T26 — Avaliação em andamento / com falha
Dois desenhos diferentes, e nenhum deles se parece com nota zero.

**Em andamento** — indica processamento. A avaliação continua mesmo se o usuário sair da tela.
**Com falha do Shifu** — erro recuperável com **Tentar novamente**, preservando a resposta já enviada. Não exige reenviar. Apresentado como problema do Shifu, **nunca** como erro pedagógico do usuário.

Enquanto houver pendência: novas tentativas bloqueadas **só nesta Habilidade**, materiais e Atividades liberados continuam navegáveis, e a recomendação espera a resolução.

#### T27 — Resultado da avaliação
Nota final + detalhes de cada parte usada:
- **Código:** todos os casos avaliados, com esperado e obtido, aprovados e reprovados. Erro de sintaxe aparece como problema da solução, com nota 0 na parte funcional, **sem fingir que todos os casos foram avaliados**
- **Critérios de IA:** cada critério com nota 0 a 100 e explicação curta

Mostra o efeito no progresso e na situação da Competência, e indica a próxima recomendação, mudança de foco ou conclusão.
**Notas menores e perda de domínio não podem ser escondidas.**
Quando uma Competência é dominada, reconhecer o marco e oferecer uma ação de continuidade — **sem abrir outra Atividade automaticamente**.
O retorno de Gamification (XP, nível, conquista) aparece **em um bloco separado**, nunca dentro do resultado pedagógico.

#### T28 — Histórico de tentativas
Todas as tentativas de aprendizagem, cada uma abrindo resposta e avaliação.
Deixar claro que apenas a avaliação **mais recente** de cada Atividade conta no progresso atual; as anteriores ficam no histórico.
Tentativa enviada **não pode parecer editável**.
O diagnóstico é exceção: nada de respostas ou avaliações individuais, só o consolidado por Competência.

#### T29 — Habilidade concluída
Resumo de evolução preservado, comparando **antes e depois**:
- progresso inicial e final de cada Competência
- resultado médio inicial e final da Habilidade
- data de início e data de conclusão

Materiais, Atividades e histórico continuam acessíveis.
Novas tentativas são permitidas e avaliadas normalmente, mas a interface precisa deixar explícito que **a nota de revisão não altera o resultado oficial**. A Habilidade não volta para aprendizado.
Não existe botão de reiniciar.

Se uma avaliação concluir a Habilidade, o usuário vê **primeiro o resultado da última Atividade e depois o resumo final** — nessa ordem.

---

### 6.5 Gamification

#### T30 — Resumo no shell
Nível atual, XP total, sequência atual. Sempre em latão, nunca em jade.
Abre a área completa.

#### T31 — Área de Progresso
Anel de nível com XP acumulado e quanto falta para o próximo.
Curva do MVP: XP necessário = 50 × L × (L − 1). Nível 2 = 100, nível 3 = 300, nível 4 = 600, nível 5 = 1000, nível 6 = 1500. Sem nível máximo.
Sequência atual e maior sequência histórica. Frase de estímulo do tipo "7 dias, pratique hoje para manter sua sequência".
Nível **nunca** apresentado como nível de conhecimento — o texto da tela precisa marcar a diferença entre aprendizagem e gamificação.

#### T32 — Calendário de atividade
Visão mensal, abre no mês atual. Navegação para meses anteriores. **Meses futuros bloqueados.**
Cinco estados, cada um com **forma própria além da cor**:
1. dia neutro (antes da primeira prática ou futuro no mês atual)
2. dia de prática
3. dia da sequência atual — distinguível dos outros dias de prática
4. dia encerrado sem prática
5. hoje ainda pendente

Não mostra quantidade de Atividades nem XP por dia. Selecionar um dia apenas confirma que houve prática.
Navegação entre meses **operável por teclado**.

#### T33 — Conquistas
Catálogo fixo, agrupado por família: Diagnóstico, Domínio, Conclusão, Sequência, Nível.
Obtidas com data. Bloqueadas com **critério e progresso até o marco**.
Conquistas retiradas do catálogo aparecem **só para quem já as obteve**, marcadas como históricas.

| Família | Conquista | Critério | XP |
|---|---|---|---|
| Diagnóstico | Primeiro Passo | 1 diagnóstico concluído | 25 |
| Diagnóstico | Explorador | 5 diagnósticos concluídos | 75 |
| Domínio | Primeiro Domínio | 1 Competência dominada | 25 |
| Domínio | Em Evolução | 10 Competências dominadas | 100 |
| Conclusão | Primeira Jornada | 1 Habilidade concluída | 50 |
| Conclusão | Colecionador de Habilidades | 5 Habilidades concluídas | 150 |
| Sequência | Consistência I | 3 dias consecutivos | 25 |
| Sequência | Consistência II | 7 dias consecutivos | 50 |
| Sequência | Consistência III | 30 dias consecutivos | 150 |
| Nível | Ascendente I | nível 5 | 50 |
| Nível | Ascendente II | nível 10 | 100 |
| Nível | Ascendente III | nível 20 | 250 |

#### T34 — Histórico de XP
Do mais novo para o mais antigo. Cada linha: quantidade, data de concessão, origem legível.
Quando a origem pedagógica foi removida, o texto continua legível **mas sem atalho de navegação**.

#### T35 — Retorno de recompensa
Agrupa os efeitos de uma prática em um único retorno. Exemplo do PRD:
```
+18 XP
Nivel 4 -> Nivel 5
Conquista desbloqueada: Consistencia II
```
Recompensas reconhecidas enquanto o usuário estava fora **ficam pendentes** e aparecem no retorno. Depois de vistas, deixam de ser novidade e não reaparecem.
Animação é complemento. **A informação essencial precisa ser textual e acessível.**
Separado visualmente do resultado de Learning.

---

### 6.6 Mentor

#### T36 — Painel do Mentor
Abre de qualquer área. Painel lateral no desktop, folha em tela cheia no mobile.
Topo: conversa atual, acesso à lista, nova conversa, medidor de cota.

#### T37 — Lista de conversas
Ordenada pela atividade mais recente. Busca por título. Renomear e excluir.
Abrir "Nova conversa" **não cria** conversa vazia no histórico — ela só existe após a primeira mensagem.
Exclusão exige confirmação e deixa claro que **não há restauração** no MVP.

#### T38 — Conversa
Somente texto. Resposta formatada, com blocos de código. Sem anexos.
A resposta aparece **progressivamente**, com botão **Cancelar**.
Ao cancelar: a mensagem do usuário permanece **pendente**, o texto parcial é descartado. Nada de texto pela metade com aparência de resposta pronta.
Falha da IA: mesma mensagem pendente + **Tentar novamente**, reutilizando a mensagem sem criar duplicata visual.
Uma resposta em andamento por conversa. Enquanto ela existe, novas mensagens ficam bloqueadas **naquela conversa**; as outras seguem independentes.
**Marcador de consulta** quando o Mentor consultar o Shifu — mostra que consultou, **não mostra o quê**.
Quando a resposta citar um Objetivo, Habilidade, material, Atividade ou resultado acessível, oferecer atalho. Se o item tiver sido removido, o texto permanece **sem navegação ativa**.
O Mentor precisa **diferenciar visualmente** quando fala com base no contexto consultado e quando dá explicação geral.

Cinco estados a desenhar: em andamento, concluída, cancelada, falha recuperável, bloqueio por cota.

#### T39 — Cota de IA
Mostra **apenas** percentual utilizado e data de renovação. Nunca tokens, chamadas ou custo.
80%: aviso de proximidade.
100%: Mentor e planejamento assistido bloqueados até a renovação. O histórico continua acessível.
A mensagem de bloqueio **não pode sugerir que a aprendizagem normal parou** — Learning segue inteiro.

---

## 7. Regras transversais de estado

Tabela de referência para não inventar componente novo a cada tela.

| Estado | Onde aparece | Regra de design |
|---|---|---|
| Carregando | qualquer | Esqueleto com a forma do conteúdo, não spinner solto |
| Vazio | Objetivos, Habilidades, conversas, conquistas | Ícone + frase curta + ação primária |
| Erro recuperável | avaliação, IA, exclusão de conta, criação de Objetivo | Frase que atribui o problema ao Shifu + **Tentar novamente** que preserva o trabalho |
| Bloqueio por cota | Mentor, planejamento assistido | Explica o limite, mostra a renovação, mantém visíveis os caminhos sem IA |
| Pendente | avaliação, mensagem do Mentor | Visual próprio, **nunca** confundível com resultado zero ou resposta pronta |
| Bloqueado | Competência não liberada, Atividade de Competência bloqueada | Cadeado + qual Competência precisa avançar |
| Somente leitura | justificativa de Habilidade, resumo final, tentativa enviada | Sem afordância de edição |

---

## 8. Acessibilidade

Requisito explícito nos PRDs de Identity, Learning, Intelligence e Gamification.

- **Nada essencial só por cor.** Situação de Competência, dias do calendário, estados de avaliação, dificuldade e cota carregam ícone e rótulo
- **Teclado em tudo que é essencial**: cadastro, entrada, recuperação, diagnóstico, envio de Atividade, navegação entre meses do calendário, etapas do lote de perguntas
- **Rótulos claros** em todo campo e ação
- Carregamento, erro, sucesso e recuperação **compreensíveis por tecnologia assistiva**
- As etapas do lote precisam anunciar de forma acessível qual é a atual e quais já foram respondidas
- O grafo de Habilidades **não pode ser a única forma** de descobrir nomes, situações ou caminhos — a visão em lista é obrigatória
- **Contraste AA verificado, não presumido.** Todos os pares de texto da seção 3.2 foram medidos. O menor é `--jade-solid` sobre `--surface` em 5,67:1, e o menor de texto sobre preenchimento é `--on-selo` sobre `--selo-fill` em 5,19:1. Ambos passam com folga em AA
- `--divider` fica abaixo de 3:1 de propósito e por isso **nunca** delimita um controle. Borda de campo, caixa de seleção e alvo clicável usam `--control-border`, medido em 3,77:1, acima do mínimo de 1.4.11
- `--text-disabled` fica em 3,47:1 e por isso é **exclusivo de estado desabilitado**. Nenhum texto informativo pode usá-lo
- Alvo de toque mínimo de 44px no mobile

---

## 9. Responsividade

Todos os fluxos abaixo funcionam em desktop e mobile, por requisito:
cadastro, entrada, confirmação, reenvio, recuperação, alteração de senha, perfil, saída, exclusão de conta, criação de Objetivos, navegação entre Habilidades, diagnóstico, materiais, Atividades, avaliações, histórico, resumo final, Mentor, cota e planejamento assistido.

Adaptações principais no mobile:
- Barra lateral vira barra inferior de 4 itens
- Mentor vira folha em tela cheia
- Lista de Competências vira cartões empilhados
- Editor de código ocupa a largura toda, com enunciado em aba separada
- Grafo de Habilidades abre por padrão na **visão em lista**
- Calendário mantém 7 colunas, com célula reduzida

---

## 10. Idioma e conteúdo

- Interface **somente em pt-BR**. Sem seletor de idioma
- Vocabulário fixo e consistente com os PRDs: **Objetivo**, **Habilidade**, **Competência**, **Atividade**, **Material de apoio**, **Diagnóstico**, **Tentativa**, **Avaliação**, **Progresso**, **Domínio**, **Mentor**, **Planejador de Objetivos**. Primeira letra maiúscula quando o termo se refere ao conceito do produto
- Nunca chamar o Mentor de "chat" nem o Planejador de "assistente"
- Nunca usar "pontos" para progresso pedagógico e "XP" para gamificação de forma trocada

---

## 11. Ordem sugerida de construção no Pencil

1. Tokens (cor, tipografia, espaço, raio, sombra)
2. Componentes base + feedback
3. Shell responsivo (sidebar desktop, barra inferior mobile, painel do Mentor)
4. T10 Home, T12 Objetivo, T21 Habilidade em aprendizado — as três telas que definem o produto
5. Fluxo de Atividade: T24, T25, T26, T27
6. Diagnóstico: T18, T19, T20
7. Planejador: T15, T16, T17
8. Mentor: T36, T37, T38, T39
9. Gamification: T30 a T35
10. Identity: T01 a T09
11. Conclusão e histórico: T28, T29
12. Passada de acessibilidade e de estados vazios em tudo

---

## 12. Pontos em aberto

Precisam de decisão do time ou dos PRDs antes de virarem tela definitiva.

| # | Assunto | Origem |
|---|---|---|
| 1 | Como o usuário escolhe e atualiza o fuso horário | Identity RP-06 declara a dependência e não define o mecanismo |
| 2 | Valor absoluto da cota mensal de IA | Intelligence RP-02 não fixa o número. A tela mostra só percentual, então isso não bloqueia o design |
| 3 | Ilustração e textura da marca | A paleta e a tipografia estão fechadas na seção 3. Falta decidir se existe ilustração, e em que grau, sem cair na estética de videogame |
| 4 | Janela de atribuição da métrica de continuidade após o Mentor | Intelligence seção 4, sem impacto em tela |

# Backlogs — Relatório de acompanhamento

Atualizado em 05/10/2026. Consolida Product Backlog, encerramento da Sprint 1 e compromisso configurado da Sprint 2. Preserva a separação entre planejamento, implementação e aceite.

## 1. Convenções e atores

- Aprendiz: pessoa que organiza Objetivos e Habilidades, pratica e utiliza orientação no Shifu.
- Usuário autenticado: pessoa com sessão ativa para ações de segurança da conta.
- Titular: pessoa cujos dados são tratados, inclusive após o encerramento da conta.
- Equipe responsável pelo conteúdo: mantém conteúdo e regras curriculares.
- Story Points medem esforço, complexidade e incerteza; não equivalem a dias. Somar pontos de tasks ao mesmo trabalho das histórias gera contagem duplicada.
- Estimativa não registrada no Jira permanece explícita, mesmo que o documento antigo contenha estimativa preliminar.
- Itens concluídos sem sprint associada não são atribuídos retroativamente à Sprint 1.

## 2. Origem e priorização

O backlog parte do desafio GSW e dos PRDs de Identity, Curriculum, Learning, Intelligence, Gamification e Communication. A referência anterior registrava o fluxo principal antes das funcionalidades complementares. As novas histórias incorporam controle de dados, práticas web e orientação contextual.

A documentação anterior existe desde 09/09/2026, antes da Sprint 1 (15/09). Para a Sprint 2, as descrições registram planejamento aprovado pela equipe, mas esta consulta não comprova o horário do refinamento anterior ao início nem traz ata de interação direta com o parceiro. Origem no desafio e interação validada são evidências distintas.

Os ranks abaixo são posições únicas da consulta atual do Product Backlog ordenada pelo campo Rank do Jira, excluindo SHIFU-2 (modelo de história). Não representam os números históricos do planejamento da Sprint 1. Prioridades reproduzem o Jira (Medium → Média). A ordem atual precisa ser conciliada pelo time com a priorização por valor; não foi modificada nesta atualização.

## 3. Product Backlog atual

| Rank | Prioridade | Jira | User Story | Valor de negócio | Estimativa | Sprint | Estado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Highest | [SHIFU-16](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-16) | Como usuário, quero realizar e retomar um diagnóstico inicial para cada Habilidade do meu Objetivo para que o Shifu determine meu ponto de partida sem misturar experiências diferentes. | Resolve a dor de não saber por onde começar e fornece o estado inicial da aprendizagem. | 8 | Sprint 1 | Concluído |
| 2 | Média | [SHIFU-17](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-17) | Como aprendiz, quero consultar as Competências, materiais e Atividades acessíveis de uma Habilidade e obter orientação contextual para compreender e percorrer o caminho oficial de aprendizagem. | Aprimora a consulta curricular existente na integração com o Mentor. | 3 | Sprint 2 | A fazer |
| 3 | Highest | [SHIFU-18](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-18) | Como usuário, quero receber uma jornada inicial após concluir o diagnóstico de uma Habilidade para saber qual Competência e Atividade devo praticar primeiro. | Converte o diagnóstico em direção prática e imediatamente acionável. | 5 | Sprint 1 | Concluído |
| 4 | Highest | [SHIFU-19](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-19) | Como usuário, quero realizar Atividades práticas da Competência em foco para exercitar o conteúdo e produzir evidências reais de aprendizagem. | Entrega o mecanismo central de prática do produto, evitando uma experiência apenas passiva. | 5 | Sprint 1 | Concluído |
| 5 | High | [SHIFU-20](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-20) | Como usuário, quero receber o resultado oficial da Atividade que realizei para entender meu desempenho e permitir que o Shifu atualize minha aprendizagem. | Produz evidência objetiva de desempenho e habilita atualização de progresso. | 8 | Sprint 1 | Concluído |
| 6 | Média | [SHIFU-21](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-21) | Como usuário, quero visualizar meu progresso por Competência e o resumo da Habilidade para perceber minha evolução real. | Torna a evolução mensurável e perceptível, atendendo diretamente ao valor central do desafio. | 5 | Sprint 1 | Concluído |
| 7 | Média | [SHIFU-22](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-22) | Como usuário, quero compreender por que recebi determinado resultado e o que devo revisar para aprender com cada tentativa, mesmo quando a IA não estiver disponível. | Melhora qualidade do feedback e transforma avaliação em orientação de aprendizagem. | Não registrada | Não associada | A fazer |
| 8 | Média | [SHIFU-23](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-23) | Como aprendiz, quero continuar usando funções disponíveis e recuperar operações pendentes para não perder meu trabalho quando serviços auxiliares falharem. | Continuidade sem resultados falsos, duplicação ou perda de tentativas. | 5 | Sprint 2 | A fazer |
| 9 | Média | [SHIFU-31](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-31) | Como usuário, quero criar uma conta com nome, e-mail e senha e confirmar meu e-mail para poder acessar as áreas protegidas do Shifu com segurança. | Viabiliza identidade persistente e acesso seguro, base necessária para toda experiência personalizada. | 5 | Sprint 1 | Concluído |
| 10 | Média | [SHIFU-32](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-32) | Como usuário, quero entrar com e-mail e senha, sair de um ou todos os dispositivos e recuperar minha senha se esquecer para manter acesso seguro à minha conta. | Permite acesso recorrente e recuperação segura sem perda da experiência do usuário. | 5 | Sprint 1 | Concluído |
| 11 | Média | [SHIFU-33](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-33) | Como aprendiz, quero manter meu nome e fuso horário e encerrar definitivamente minha conta para controlar meu perfil e meus dados no Shifu. | Autonomia sobre perfil e encerramento seguro da participação. | 13 | Sprint 2 | A fazer |
| 12 | Média | [SHIFU-34](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-34) | Como usuário, quero criar um Objetivo com título e descrição, sem depender de IA, para organizar minha intenção de aprendizagem. | Permite iniciar a jornada de aprendizagem com baixo risco e sem dependência de IA. | 3 | Sprint 1 | Concluído |
| 13 | High | [SHIFU-35](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-35) | Como usuário, quero adicionar Habilidades a um Objetivo e ver como elas se relacionam para estudar mais de uma Habilidade sem misturar seus resultados. | Estrutura a experiência individual de aprendizagem e separa corretamente os contextos de progresso. | 3 | Sprint 1 | Concluído |
| 14 | Média | [SHIFU-36](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-36) | Como aprendiz, quero remover uma Habilidade ou Objetivo com consequências claras para eliminar experiências que não desejo manter sem afetar outras. | Preserva exclusão consistente ao integrar Mentor e o novo ciclo de dados. | 3 | Sprint 2 | A fazer |
| 15 | Média | [SHIFU-37](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-37) | Como usuário, quero que meu progresso reflita meu desempenho mais recente em cada Atividade para que repetir a mesma Atividade não infle artificialmente meu progresso. | Aumenta a confiabilidade da medida de aprendizagem. | Não registrada | Não associada | Concluído |
| 16 | Média | [SHIFU-38](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-38) | Como usuário, quero que o sistema identifique automaticamente em qual Competência devo focar e libere conteúdo conforme evoluo para não perder tempo decidindo sozinho por onde continuar. | Implementa adaptação real da experiência com base em desempenho. | Não registrada | Não associada | Concluído |
| 17 | Média | [SHIFU-39](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-39) | Como usuário, quero receber a recomendação da próxima Atividade adequada ao meu estado atual, incluindo reforço quando necessário, para praticar sempre no nível certo. | Mantém a jornada personalizada e reduz abandono por dificuldade inadequada. | Não registrada | Não associada | Concluído |
| 18 | High | [SHIFU-40](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-40) | Como equipe responsável pelo conteúdo, quero definir uma sequência explícita de materiais de apoio e Atividades por Competência para que Learning apresente teoria e prática numa ordem coerente. | Garante uma fonte curricular estável e evita conteúdo ou ordem inventados pela aplicação. | 3 | Sprint 1 | Concluído |
| 19 | Highest | [SHIFU-41](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-41) | Como equipe responsável pelo conteúdo, quero definir para cada Atividade como ela deve ser avaliada para que Learning tenha uma regra clara antes de o usuário responder. | Torna as atividades objetivamente avaliáveis e sustenta diagnóstico, resultado e progresso. | 8 | Sprint 1 | Concluído |
| 20 | Média | [SHIFU-42](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-42) | Como usuário, quero descrever livremente o que desejo aprender na tela inicial, sem conhecer as Habilidades existentes, para iniciar um planejamento assistido por IA. | Reduz a barreira de entrada para quem sabe o objetivo, mas não conhece a estrutura curricular. | Não registrada | Não associada | Concluído |
| 21 | Média | [SHIFU-43](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-43) | Como aprendiz, quero esclarecer minha intenção em lotes de perguntas objetivas para receber um planejamento coerente com as Habilidades disponíveis. | Transforma uma intenção ambígua em contexto útil, sem entrevista desnecessária. | 8 | Sprint 2 | A fazer |
| 22 | Média | [SHIFU-44](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-44) | Como aprendiz, quero revisar uma proposta válida, editar sua redação ou reiniciar o planejamento e confirmar sua criação para controlar meu Objetivo antes de persistir dados em Learning. | Planejamento explicável com criação íntegra e confirmação sob controle do usuário. | 13 | Sprint 2 | A fazer |
| 23 | Média | [SHIFU-45](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-45) | Como aprendiz, quero organizar conversas privadas e retomá-las com continuidade para manter minhas dúvidas sem misturar assuntos. | Histórico confiável e continuidade em conversas longas. | 8 | Sprint 2 | A fazer |
| 24 | Média | [SHIFU-46](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-46) | Como aprendiz, quero que o Mentor compreenda referências ao meu contexto no Shifu para receber ajuda sem copiar dados manualmente. | Orientação baseada em informações atuais e autorizadas, evitando respostas inventadas. | 8 | Sprint 2 | A fazer |
| 25 | Média | [SHIFU-47](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-47) | Como aprendiz, quero dicas progressivas e análise dos meus erros para aprender sem que o Mentor substitua minha prática. | Assistência útil preservando o desafio e a autoridade pedagógica. | 5 | Sprint 2 | A fazer |
| 26 | Média | [SHIFU-48](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-48) | Como aprendiz, quero ganhar XP pela prática avaliada e por marcos confirmados para reconhecer minha evolução sem alterar meus resultados pedagógicos. | Recompensa consistente e explicável para prática e evolução. | 8 | Sprint 2 | A fazer |
| 27 | Média | [SHIFU-49](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-49) | Como aprendiz, quero acompanhar meu nível e sequência de prática para reconhecer minha constância global. | Reconhecimento correto da constância, independente do Objetivo. | 5 | Sprint 2 | A fazer |
| 28 | Média | [SHIFU-50](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-50) | Como aprendiz, quero desbloquear conquistas e consultar seus critérios para acompanhar marcos da minha trajetória. | Incentivo objetivo de longo prazo com progresso transparente. | 8 | Sprint 2 | Fazendo |
| 29 | Média | [SHIFU-51](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-51) | Como aprendiz, quero consultar meu resumo de gamificação, calendário e histórico de XP para entender minha constância e a origem das recompensas. | Visibilidade consolidada e auditável da evolução motivacional. | 5 | Sprint 2 | A fazer |
| 30 | Média | [SHIFU-52](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-52) | Como usuário autenticado, quero alterar minha senha informando a senha atual para proteger minha conta e encerrar os demais acessos. | Controle seguro das credenciais sem perder a sessão atual. | 3 | Sprint 2 | A fazer |
| 31 | Média | [SHIFU-53](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-53) | Como usuário, quero concluir uma Habilidade e continuar consultando seu conteúdo, progresso e tentativas para reconhecer minha evolução sem perder o histórico de aprendizagem. | Fecha o ciclo de aprendizagem e preserva evidência de evolução. | Não registrada | Não associada | A fazer |
| 32 | Média | [SHIFU-54](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-54) | Como aprendiz, quero acompanhar o uso e renovação da minha cota compartilhada para usar Mentor e Planejador com previsibilidade. | Controle de consumo justo sem bloquear aprendizagem que não depende de IA. | 8 | Sprint 2 | A fazer |
| 33 | Média | [SHIFU-55](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-55) | Como aprendiz, quero acompanhar, cancelar e repetir respostas em falha para manter controle da conversa sem perder ou duplicar mensagens. | Recuperação previsível da conversa e preservação do trabalho. | 5 | Sprint 2 | A fazer |
| 34 | Média | [SHIFU-106](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-106) | Como aprendiz, quero perceber, consultar, editar e excluir memórias usadas pelo Mentor para receber orientação personalizada com controle sobre minhas informações. | Personalização controlável sem confundir declarações com domínio pedagógico. | 13 | Sprint 2 | A fazer |
| 35 | Média | [SHIFU-107](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-107) | Como aprendiz, quero enviar arquivos e receber explicações com indicação de fontes e limitações para compreender materiais sem perder o controle dos meus anexos. | Ajuda sobre arquivos reais com privacidade e transparência de leitura. | 13 | Sprint 2 | A fazer |
| 36 | Média | [SHIFU-108](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-108) | Como aprendiz, quero confirmar propostas de adição ou remoção de Habilidades para ajustar meus Objetivos com destino e consequências claros. | Ação assistida sob confirmação explícita e autoridade de Learning. | 8 | Sprint 2 | A fazer |
| 37 | Média | [SHIFU-109](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-109) | Como aprendiz, quero ditar uma mensagem e revisar a transcrição antes de enviá-la para compor minhas dúvidas por voz sem guardar áudio no histórico. | Alternativa de composição acessível com envio sob controle do usuário. | 5 | Sprint 2 | A fazer |
| 38 | Média | [SHIFU-110](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-110) | Como aprendiz, quero editar e experimentar uma página web e receber sua avaliação para praticar HTML, CSS e JavaScript com resultado preservado. | Amplia prática aplicada a páginas web completas. | 8 | Sprint 2 | A fazer |
| 39 | Média | [SHIFU-111](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-111) | Como aprendiz, quero construir e experimentar uma aplicação React para praticar componentes e receber avaliação da minha resposta. | Prática aplicada de React com permissões curriculares explícitas. | 8 | Sprint 2 | A fazer |
| 40 | Média | [SHIFU-112](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-112) | Como aprendiz, quero experimentar interface e API em uma questão integrada para desenvolver uma solução full stack e receber avaliação conjunta. | Prática integrada entre frontend e API com resposta histórica única. | 13 | Sprint 2 | A fazer |
| 41 | Média | [SHIFU-113](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-113) | Como pessoa que utiliza ou deixou o Shifu, quero consultar o aviso público e encontrar o atendimento para entender o tratamento dos meus dados. | Transparência e acesso ao canal de direitos antes e após autenticação. | 3 | Sprint 2 | A fazer |
| 42 | Média | [SHIFU-114](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-114) | Como titular, inclusive após encerrar a conta, quero solicitar acesso, correção e explicação ou revisão aplicável para exercer meus direitos e acompanhar o tratamento dos meus dados. | Atendimento efetivo e seguro, além da simples publicação de um contato. | 5 | Sprint 2 | A fazer |
| 43 | Média | [SHIFU-115](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-115) | Como aprendiz, quero perceber níveis e conquistas confirmados, inclusive ao retornar ao Shifu, para reconhecer minha prática sem receber novidades repetidas. | Retorno motivacional oportuno e coerente com recompensas efetivamente concedidas. | 5 | Sprint 2 | Fazendo |
| 44 | Média | [SHIFU-116](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-116) | Como titular que encerrou a conta, quero que retenção e restauração respeitem minha exclusão para que meus dados não voltem a ficar disponíveis. | Cumpre o ciclo de vida também fora das bases ativas. | 8 | Sprint 2 | A fazer |

**44 histórias de produto.** SHIFU-2 é um modelo e não integra o backlog funcional. Priorização atual e escolha das 27 histórias precisam ser conciliadas pelo time: SHIFU-22 e SHIFU-53 permanecem pendentes sem estimativa/sprint. A tabela reproduz a ordem do Jira, sem repriorização automática.

## 4. Sprint Backlog — Sprint 1 finalizada

## Encerramento e resultado

| Indicador | Resultado |
| --- | --- |
| Estado | Finalizada; sprint closed no Jira |
| Período | 15/09/2026 a 27/09/2026, America/Sao_Paulo |
| Encerramento registrado | 28/09/2026 às 20:42:47, America/Sao_Paulo |
| Capacidade inicial de referência | 58 SP |
| Meta | Conta → Objetivo → Habilidade → Diagnóstico → Jornada inicial → Atividade → Resultado → Progresso |
| Compromisso concluído | 11 de 11 User Stories / 58 de 58 SP |
| Tasks concluídas | 21 de 21 |
| Tickets pendentes na sprint | Nenhum: 32 de 32 Concluído |
| Previsão extra sem compromisso | Nenhuma registrada no planejamento original |
| Incremento | Fundação de conta, Objetivos/Habilidades, currículo, diagnóstico, jornada, prática, resultado e progresso |
| Evidência complementar | documentation/sprints/sprint-1.md e sprint-1-logic-demo.md |
| Vídeo / ata de aceite | Link não identificado nas fontes consultadas |

O compromisso está integralmente concluído no Jira e o relatório local registra o ciclo entregue. Esta atualização documental não executou novamente a aplicação; a demonstração e seus limites permanecem no relatório existente. A conclusão dos tickets não comprova retroativamente todos os itens do DoR nem substitui evidência de execução.

| Rank | Prioridade | Jira | User Story | Estimativa | Sprint | Estado | Responsável |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Highest | [SHIFU-16](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-16) | Como usuário, quero realizar e retomar um diagnóstico inicial para cada Habilidade do meu Objetivo para que o Shifu determine meu ponto de partida sem misturar experiências diferentes. | 8 | 1 | Concluído | Não atribuído |
| 3 | Highest | [SHIFU-18](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-18) | Como usuário, quero receber uma jornada inicial após concluir o diagnóstico de uma Habilidade para saber qual Competência e Atividade devo praticar primeiro. | 5 | 1 | Concluído | Não atribuído |
| 4 | Highest | [SHIFU-19](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-19) | Como usuário, quero realizar Atividades práticas da Competência em foco para exercitar o conteúdo e produzir evidências reais de aprendizagem. | 5 | 1 | Concluído | Não atribuído |
| 5 | High | [SHIFU-20](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-20) | Como usuário, quero receber o resultado oficial da Atividade que realizei para entender meu desempenho e permitir que o Shifu atualize minha aprendizagem. | 8 | 1 | Concluído | Não atribuído |
| 6 | Média | [SHIFU-21](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-21) | Como usuário, quero visualizar meu progresso por Competência e o resumo da Habilidade para perceber minha evolução real. | 5 | 1 | Concluído | Não atribuído |
| 9 | Média | [SHIFU-31](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-31) | Como usuário, quero criar uma conta com nome, e-mail e senha e confirmar meu e-mail para poder acessar as áreas protegidas do Shifu com segurança. | 5 | 1 | Concluído | Não atribuído |
| 10 | Média | [SHIFU-32](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-32) | Como usuário, quero entrar com e-mail e senha, sair de um ou todos os dispositivos e recuperar minha senha se esquecer para manter acesso seguro à minha conta. | 5 | 1 | Concluído | Não atribuído |
| 12 | Média | [SHIFU-34](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-34) | Como usuário, quero criar um Objetivo com título e descrição, sem depender de IA, para organizar minha intenção de aprendizagem. | 3 | 1 | Concluído | Não atribuído |
| 13 | High | [SHIFU-35](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-35) | Como usuário, quero adicionar Habilidades a um Objetivo e ver como elas se relacionam para estudar mais de uma Habilidade sem misturar seus resultados. | 3 | 1 | Concluído | Não atribuído |
| 18 | High | [SHIFU-40](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-40) | Como equipe responsável pelo conteúdo, quero definir uma sequência explícita de materiais de apoio e Atividades por Competência para que Learning apresente teoria e prática numa ordem coerente. | 3 | 1 | Concluído | Não atribuído |
| 19 | Highest | [SHIFU-41](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-41) | Como equipe responsável pelo conteúdo, quero definir para cada Atividade como ela deve ser avaliada para que Learning tenha uma regra clara antes de o usuário responder. | 8 | 1 | Concluído | Não atribuído |

### Histórico de estimativas e seleção

O planejamento original comprometeu as 11 histórias acima, 58 SP, sem extras. O critério de sucesso foi o ciclo principal persistido, inicialmente com Lógica de Programação e sem dependência de IA. Tasks adicionais de plataforma e interface constam no relatório de resultado local, sem inflar os pontos do compromisso.

### DoR histórico da Sprint 1

| Critério | Registro anterior | Situação deste relatório |
| --- | --- | --- |
| História, critérios, regras e estimativas | Atende | Mantido como registro histórico |
| Dependências, PRDs e arquitetura | Atende | Mantido como registro histórico |
| Modelo de dados e estratégia de testes | A validar pelo time | Sem comprovação retroativa consolidada |
| Tasks e compreensão coletiva | Responsabilidade do time | Jira confirma 21 tasks concluídas; isso não comprova isoladamente o DoR prévio |

## 5. Sprint Backlog — Sprint 2

## Identificação

| Campo | Definição |
| --- | --- |
| Sprint | SHIFU Sprint 2 — ID 498, quadro 331 |
| Estado | Ativa / em andamento |
| Período | 05/10/2026 a 25/10/2026, America/Sao_Paulo |
| Capacidade estimada da equipe | Não registrada na fonte consultada |
| Referência histórica | Sprint 1: 58 SP concluídos em 11 histórias |
| Compromisso configurado | 27 User Stories, 197 SP |
| Tasks | 28; sem soma adicional de pontos |
| Previsão extra sem compromisso | Nenhum item explicitamente classificado como extra |

## Meta e síntese do escopo

**Campo de meta no Jira: vazio.** A formulação abaixo é uma síntese documental das histórias selecionadas, a validar pela equipe como meta única e estável; não constitui aprovação retroativa:

> Ampliar o ciclo de aprendizagem entregue na Sprint 1 com planejamento assistido, Mentor contextual e controlável, prática de projetos web, gamificação e gestão segura da conta e dos dados, preservando a aprendizagem diante de falhas dos serviços auxiliares.

Todos os 27 tickets de história explicitam “Compromisso da Sprint 2”. Não foram reclassificados como extras. O compromisso de 197 SP equivale a aproximadamente 3,4 vezes os 58 SP concluídos na Sprint 1. Períodos e composição do trabalho diferem; esse número não comprova capacidade. É necessário registrar a capacidade aprovada e reconciliá-la com o compromisso.

## User Stories comprometidas

Os ranks abaixo são posições únicas da consulta atual do Product Backlog ordenada pelo campo Rank do Jira, excluindo SHIFU-2 (modelo de história). Não representam os números históricos do planejamento da Sprint 1. Prioridades reproduzem o Jira (Medium → Média). A ordem atual precisa ser conciliada pelo time com a priorização por valor; não foi modificada nesta atualização.

| Rank | Prioridade | Jira | User Story | Estimativa | Sprint | Estado | Responsável |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | Média | [SHIFU-17](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-17) | Como aprendiz, quero consultar as Competências, materiais e Atividades acessíveis de uma Habilidade e obter orientação contextual para compreender e percorrer o caminho oficial de aprendizagem. | 3 | 2 | A fazer | João Pedro Carvalho |
| 8 | Média | [SHIFU-23](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-23) | Como aprendiz, quero continuar usando funções disponíveis e recuperar operações pendentes para não perder meu trabalho quando serviços auxiliares falharem. | 5 | 2 | A fazer | João Gabriel |
| 11 | Média | [SHIFU-33](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-33) | Como aprendiz, quero manter meu nome e fuso horário e encerrar definitivamente minha conta para controlar meu perfil e meus dados no Shifu. | 13 | 2 | A fazer | João Gabriel |
| 14 | Média | [SHIFU-36](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-36) | Como aprendiz, quero remover uma Habilidade ou Objetivo com consequências claras para eliminar experiências que não desejo manter sem afetar outras. | 3 | 2 | A fazer | João Gabriel |
| 21 | Média | [SHIFU-43](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-43) | Como aprendiz, quero esclarecer minha intenção em lotes de perguntas objetivas para receber um planejamento coerente com as Habilidades disponíveis. | 8 | 2 | A fazer | Thigz |
| 22 | Média | [SHIFU-44](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-44) | Como aprendiz, quero revisar uma proposta válida, editar sua redação ou reiniciar o planejamento e confirmar sua criação para controlar meu Objetivo antes de persistir dados em Learning. | 13 | 2 | A fazer | Thigz |
| 23 | Média | [SHIFU-45](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-45) | Como aprendiz, quero organizar conversas privadas e retomá-las com continuidade para manter minhas dúvidas sem misturar assuntos. | 8 | 2 | A fazer | João Pedro Carvalho |
| 24 | Média | [SHIFU-46](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-46) | Como aprendiz, quero que o Mentor compreenda referências ao meu contexto no Shifu para receber ajuda sem copiar dados manualmente. | 8 | 2 | A fazer | João Pedro Carvalho |
| 25 | Média | [SHIFU-47](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-47) | Como aprendiz, quero dicas progressivas e análise dos meus erros para aprender sem que o Mentor substitua minha prática. | 5 | 2 | A fazer | João Pedro Carvalho |
| 26 | Média | [SHIFU-48](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-48) | Como aprendiz, quero ganhar XP pela prática avaliada e por marcos confirmados para reconhecer minha evolução sem alterar meus resultados pedagógicos. | 8 | 2 | A fazer | Kauan Fonseca |
| 27 | Média | [SHIFU-49](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-49) | Como aprendiz, quero acompanhar meu nível e sequência de prática para reconhecer minha constância global. | 5 | 2 | A fazer | Kauan Fonseca |
| 28 | Média | [SHIFU-50](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-50) | Como aprendiz, quero desbloquear conquistas e consultar seus critérios para acompanhar marcos da minha trajetória. | 8 | 2 | Fazendo | Kauan Fonseca |
| 29 | Média | [SHIFU-51](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-51) | Como aprendiz, quero consultar meu resumo de gamificação, calendário e histórico de XP para entender minha constância e a origem das recompensas. | 5 | 2 | A fazer | Kauan Fonseca |
| 30 | Média | [SHIFU-52](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-52) | Como usuário autenticado, quero alterar minha senha informando a senha atual para proteger minha conta e encerrar os demais acessos. | 3 | 2 | A fazer | João Gabriel |
| 32 | Média | [SHIFU-54](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-54) | Como aprendiz, quero acompanhar o uso e renovação da minha cota compartilhada para usar Mentor e Planejador com previsibilidade. | 8 | 2 | A fazer | Thigz |
| 33 | Média | [SHIFU-55](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-55) | Como aprendiz, quero acompanhar, cancelar e repetir respostas em falha para manter controle da conversa sem perder ou duplicar mensagens. | 5 | 2 | A fazer | João Pedro Carvalho |
| 34 | Média | [SHIFU-106](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-106) | Como aprendiz, quero perceber, consultar, editar e excluir memórias usadas pelo Mentor para receber orientação personalizada com controle sobre minhas informações. | 13 | 2 | A fazer | João Pedro Carvalho |
| 35 | Média | [SHIFU-107](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-107) | Como aprendiz, quero enviar arquivos e receber explicações com indicação de fontes e limitações para compreender materiais sem perder o controle dos meus anexos. | 13 | 2 | A fazer | João Pedro Carvalho |
| 36 | Média | [SHIFU-108](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-108) | Como aprendiz, quero confirmar propostas de adição ou remoção de Habilidades para ajustar meus Objetivos com destino e consequências claros. | 8 | 2 | A fazer | João Pedro Carvalho |
| 37 | Média | [SHIFU-109](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-109) | Como aprendiz, quero ditar uma mensagem e revisar a transcrição antes de enviá-la para compor minhas dúvidas por voz sem guardar áudio no histórico. | 5 | 2 | A fazer | João Pedro Carvalho |
| 38 | Média | [SHIFU-110](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-110) | Como aprendiz, quero editar e experimentar uma página web e receber sua avaliação para praticar HTML, CSS e JavaScript com resultado preservado. | 8 | 2 | A fazer | João Gabriel |
| 39 | Média | [SHIFU-111](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-111) | Como aprendiz, quero construir e experimentar uma aplicação React para praticar componentes e receber avaliação da minha resposta. | 8 | 2 | A fazer | João Gabriel |
| 40 | Média | [SHIFU-112](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-112) | Como aprendiz, quero experimentar interface e API em uma questão integrada para desenvolver uma solução full stack e receber avaliação conjunta. | 13 | 2 | A fazer | João Gabriel |
| 41 | Média | [SHIFU-113](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-113) | Como pessoa que utiliza ou deixou o Shifu, quero consultar o aviso público e encontrar o atendimento para entender o tratamento dos meus dados. | 3 | 2 | A fazer | João Gabriel |
| 42 | Média | [SHIFU-114](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-114) | Como titular, inclusive após encerrar a conta, quero solicitar acesso, correção e explicação ou revisão aplicável para exercer meus direitos e acompanhar o tratamento dos meus dados. | 5 | 2 | A fazer | João Gabriel |
| 43 | Média | [SHIFU-115](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-115) | Como aprendiz, quero perceber níveis e conquistas confirmados, inclusive ao retornar ao Shifu, para reconhecer minha prática sem receber novidades repetidas. | 5 | 2 | Fazendo | Kauan Fonseca |
| 44 | Média | [SHIFU-116](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-116) | Como titular que encerrou a conta, quero que retenção e restauração respeitem minha exclusão para que meus dados não voltem a ficar disponíveis. | 8 | 2 | A fazer | gabrielsoliveira1606 |

**Total: 27 histórias / 197 SP.** Entregas anteriores são base; somente o incremento desta sprint é pontuado. Tasks não recebem pontos adicionais pelo mesmo trabalho.

## Valor de negócio

| História | Valor |
| --- | --- |
| [SHIFU-17](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-17) | Aprimora a consulta curricular existente na integração com o Mentor. |
| [SHIFU-23](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-23) | Continuidade sem resultados falsos, duplicação ou perda de tentativas. |
| [SHIFU-33](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-33) | Autonomia sobre perfil e encerramento seguro da participação. |
| [SHIFU-36](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-36) | Preserva exclusão consistente ao integrar Mentor e o novo ciclo de dados. |
| [SHIFU-43](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-43) | Transforma uma intenção ambígua em contexto útil, sem entrevista desnecessária. |
| [SHIFU-44](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-44) | Planejamento explicável com criação íntegra e confirmação sob controle do usuário. |
| [SHIFU-45](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-45) | Histórico confiável e continuidade em conversas longas. |
| [SHIFU-46](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-46) | Orientação baseada em informações atuais e autorizadas, evitando respostas inventadas. |
| [SHIFU-47](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-47) | Assistência útil preservando o desafio e a autoridade pedagógica. |
| [SHIFU-48](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-48) | Recompensa consistente e explicável para prática e evolução. |
| [SHIFU-49](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-49) | Reconhecimento correto da constância, independente do Objetivo. |
| [SHIFU-50](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-50) | Incentivo objetivo de longo prazo com progresso transparente. |
| [SHIFU-51](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-51) | Visibilidade consolidada e auditável da evolução motivacional. |
| [SHIFU-52](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-52) | Controle seguro das credenciais sem perder a sessão atual. |
| [SHIFU-54](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-54) | Controle de consumo justo sem bloquear aprendizagem que não depende de IA. |
| [SHIFU-55](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-55) | Recuperação previsível da conversa e preservação do trabalho. |
| [SHIFU-106](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-106) | Personalização controlável sem confundir declarações com domínio pedagógico. |
| [SHIFU-107](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-107) | Ajuda sobre arquivos reais com privacidade e transparência de leitura. |
| [SHIFU-108](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-108) | Ação assistida sob confirmação explícita e autoridade de Learning. |
| [SHIFU-109](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-109) | Alternativa de composição acessível com envio sob controle do usuário. |
| [SHIFU-110](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-110) | Amplia prática aplicada a páginas web completas. |
| [SHIFU-111](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-111) | Prática aplicada de React com permissões curriculares explícitas. |
| [SHIFU-112](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-112) | Prática integrada entre frontend e API com resposta histórica única. |
| [SHIFU-113](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-113) | Transparência e acesso ao canal de direitos antes e após autenticação. |
| [SHIFU-114](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-114) | Atendimento efetivo e seguro, além da simples publicação de um contato. |
| [SHIFU-115](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-115) | Retorno motivacional oportuno e coerente com recompensas efetivamente concedidas. |
| [SHIFU-116](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-116) | Cumpre o ciclo de vida também fora das bases ativas. |

## Frentes e integração

- Learning: navegação contextual, remoção consistente e recuperação de operações; prática HTML/CSS/JavaScript, React e React + Fastify.
- Intelligence: entrevista e proposta de Objetivo, conversas, contexto autorizado, orientação pedagógica, cota, recuperação, memórias, anexos, ações confirmadas e ditado.
- Gamification: XP, níveis, sequência, conquistas, visão geral, calendário, histórico e celebrações sem repetição.
- Identity e privacidade: perfil/fuso, senha, encerramento coordenado, aviso público, atendimento e retenção/restauração.
- Plataforma: IaC, staging, entrega contínua, qualidade e telemetria.

As dependências detalhadas e a parcela própria de cada história estão nos tickets. Concluir uma task compartilhada não conclui automaticamente todas as histórias relacionadas.

## Definition of Ready

| Critério | Situação registrada | Evidência / pendência |
| --- | --- | --- |
| Título, descrição, ator e valor | Documentado | 27 histórias descrevem resultado para aprendiz, pessoa que utiliza o Shifu ou titular. |
| Critérios de aceitação e regras | Documentado | Critérios CA, limites e rastreabilidade nos tickets. |
| Estimativa pela equipe | Estimativa registrada; confirmação coletiva não comprovada | 197 SP em Fibonacci; descrições tratam estimativas como iniciais. |
| Sem dependências bloqueadoras | Não comprovado | Dependências entre tasks e histórias explicitadas; conclusão das tasks não equivale a aceite da US. |
| Compreensão validada com o time | Checklist marcado nos tickets; ata não vinculada | Não inferir consenso completo apenas da configuração da sprint. |
| Design/documentação | Referências identificadas | PRDs e referências por ticket; disponibilidade integral do design precisa ser conferida por frente. |
| Regras de negócio detalhadas | Documentado | Critérios e requisitos RP/JN citados nas histórias. |
| Modelo de dados disponível | A confirmar por frente | Não há comprovação consolidada para todas as integrações novas. |
| Estratégia de testes definida | Diretrizes registradas | Tickets pedem testes, jornada persistida, desktop/mobile, teclado e falhas; planos completos por frente ainda precisam ser vinculados. |

DoR não é declarado integralmente atendido. SHIFU-113 depende de decisões aprovadas de conteúdo da política; SHIFU-114 compromete procedimento e ensaio próprios; SHIFU-115 inclui apresentação e controle de novidades; SHIFU-116 inclui retenção e restauração segura além das tasks de infraestrutura.

## Tasks e responsáveis

| Jira | Tipo | Trabalho | Responsável | Estado | Histórias relacionadas |
| --- | --- | --- | --- | --- | --- |
| [SHIFU-78](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-78) | Logical Task | Criar IAC básico do projeto | gabrielsoliveira1606 | A fazer | Trabalho técnico transversal; sem US referenciada nesta consulta |
| [SHIFU-79](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-79) | Dev Task | Implementar processamento de conquistas e aba de Conquistas | Kauan Fonseca | Fazendo | [SHIFU-50](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-50), [SHIFU-115](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-115) |
| [SHIFU-80](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-80) | Dev Task | Implementar calendário de prática e cálculo de sequências | Kauan Fonseca | A fazer | [SHIFU-49](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-49), [SHIFU-51](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-51) |
| [SHIFU-81](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-81) | Dev Task | Implementar persistência e aba de Histórico de XP | Kauan Fonseca | A fazer | [SHIFU-51](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-51) |
| [SHIFU-82](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-82) | Dev Task | Implementar visão geral de Gamificação e cálculo de níveis | Kauan Fonseca | A fazer | [SHIFU-49](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-49), [SHIFU-51](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-51), [SHIFU-115](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-115) |
| [SHIFU-83](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-83) | Logical Task | Provisionar infraestrutura de staging do Shifu com Terraform e validar o laboratório S3 | gabrielsoliveira1606 | A fazer | [SHIFU-116](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-116) |
| [SHIFU-84](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-84) | Dev Task | Implementar concessão de XP e integração das recompensas no resultado da Atividade | Kauan Fonseca | A fazer | [SHIFU-23](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-23), [SHIFU-48](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-48), [SHIFU-115](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-115) |
| [SHIFU-85](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-85) | Logical Task | Implementar CD de Terraform e aplicações do Shifu para staging | gabrielsoliveira1606 | A fazer | [SHIFU-116](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-116) |
| [SHIFU-86](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-86) | Dev Task | Implementar questões de página HTML/CSS/JavaScript em Atividades de aprendizagem | João Gabriel | A fazer | [SHIFU-23](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-23), [SHIFU-110](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-110) |
| [SHIFU-87](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-87) | Logical Task | Integrar SonarCloud ao CI do Web e da API com cobertura, quality gate e comentários nos PRs | gabrielsoliveira1606 | A fazer | Trabalho técnico transversal; sem US referenciada nesta consulta |
| [SHIFU-88](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-88) | Dev Task | Implementar questões React em Atividades de aprendizagem | João Gabriel | A fazer | [SHIFU-23](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-23), [SHIFU-111](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-111) |
| [SHIFU-89](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-89) | Dev Task | Implementar classificação e recuperação de Habilidades com PLN | Thigz | A fazer | [SHIFU-43](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-43), [SHIFU-44](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-44) |
| [SHIFU-90](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-90) | Dev Task | Implementar questões integradas React + Fastify em Atividades de aprendizagem | João Gabriel | A fazer | [SHIFU-23](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-23), [SHIFU-112](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-112) |
| [SHIFU-91](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-91) | Dev Task | Implementar fluxo do Planejador de Objetivos no backend | Thigz | A fazer | [SHIFU-23](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-23), [SHIFU-43](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-43), [SHIFU-44](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-44), [SHIFU-54](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-54) |
| [SHIFU-92](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-92) | Dev Task | Implementar interface da entrevista do Planejador de Objetivos | Thigz | A fazer | [SHIFU-43](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-43) |
| [SHIFU-93](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-93) | Dev Task | Implementar revisão da proposta e reinício do planejamento | Thigz | A fazer | [SHIFU-44](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-44) |
| [SHIFU-94](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-94) | Logical Task | Implementar telemetria estruturada em JSON no Web/BFF e na API | gabrielsoliveira1606 | A fazer | [SHIFU-116](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-116) |
| [SHIFU-95](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-95) | Dev Task | Integrar criação do Objetivo planejado com Learning | Thigz | A fazer | [SHIFU-23](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-23), [SHIFU-44](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-44) |
| [SHIFU-96](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-96) | Dev Task | Implementar página pública de Política de privacidade e seus pontos de acesso | João Gabriel | A fazer | [SHIFU-113](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-113), [SHIFU-114](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-114) |
| [SHIFU-97](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-97) | Dev Task | Implementar perfil e segurança em Minha conta | João Gabriel | A fazer | [SHIFU-33](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-33), [SHIFU-52](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-52) |
| [SHIFU-98](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-98) | Dev Task | Implementar exclusão definitiva da conta e eliminação coordenada dos dados | João Gabriel | A fazer | [SHIFU-33](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-33), [SHIFU-36](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-36), [SHIFU-114](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-114), [SHIFU-116](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-116) |
| [SHIFU-99](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-99) | Dev Task | Implementar gestão de conversas do Mentor | João Pedro Carvalho | A fazer | [SHIFU-45](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-45) |
| [SHIFU-100](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-100) | Dev Task | Implementar respostas contextuais e recuperação | João Pedro Carvalho | A fazer | [SHIFU-17](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-17), [SHIFU-23](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-23), [SHIFU-46](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-46), [SHIFU-47](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-47), [SHIFU-54](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-54), [SHIFU-55](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-55) |
| [SHIFU-101](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-101) | Dev Task | Implementar memórias do aprendiz | João Pedro Carvalho | A fazer | [SHIFU-46](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-46), [SHIFU-106](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-106) |
| [SHIFU-102](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-102) | Dev Task | Implementar resumo e continuidade da conversa | João Pedro Carvalho | A fazer | [SHIFU-45](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-45) |
| [SHIFU-103](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-103) | Dev Task | Implementar anexos e análise de arquivos | João Pedro Carvalho | A fazer | [SHIFU-107](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-107) |
| [SHIFU-104](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-104) | Dev Task | Implementar ações confirmadas do Mentor | João Pedro Carvalho | A fazer | [SHIFU-36](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-36), [SHIFU-47](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-47), [SHIFU-106](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-106), [SHIFU-108](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-108) |
| [SHIFU-105](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-105) | Dev Task | Implementar ditado por áudio | João Pedro Carvalho | A fazer | [SHIFU-109](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-109) |

A distribuição acima reproduz o Jira. Duração inferior a 8 horas, datas de entrega e uma task em progresso por pessoa devem ser acompanhadas pelo time; não estão declaradas como comprovadas por esta tabela. O burndown deve ser acompanhado no quadro da sprint.

## Estado e resultado

| Indicador | Situação em 05/10/2026 |
| --- | --- |
| Histórias concluídas | 0 de 27 |
| SP concluídos | 0 de 197 |
| Histórias em andamento | SHIFU-50 e SHIFU-115 |
| Tasks em andamento | SHIFU-79 |
| Total de tickets | 55: 52 A fazer e 3 Fazendo |
| Meta atingida | Ainda não aferida; sprint ativa |
| Incremento demonstrável / evidências | A registrar após integração e aceite |
| Encerramento | Ainda não realizado |

## Pendências de planejamento e acompanhamento

1. Registrar e confirmar a meta única da Sprint 2, preservando-a durante a execução.
2. Registrar capacidade aprovada e justificar o compromisso de 197 SP perante a referência histórica.
3. Conciliar seleção/prioridade com os itens ainda pendentes do Product Backlog, inclusive SHIFU-22 e SHIFU-53, sem estimativa atual no Jira.
4. Fechar e vincular as evidências de DoR, decisões de conteúdo e planos por frente.
5. Registrar aceite por história, evidências do incremento e resultado final, preservando o histórico da Sprint 1.



## 6. Evidências e manutenção

| Registro | Situação |
| --- | --- |
| Rank único e valor explícito | 44 linhas de produto; ordem atual do Jira |
| Formato do backlog | Rank, Prioridade, User Story, Estimativa, Sprint |
| Sprint 1 | Finalizada: 58 SP / 11 histórias / 21 tasks |
| Sprint 2 | Ativa: 197 SP / 27 histórias / 28 tasks |
| Capacidade Sprint 2 | Não comprovada; 58 SP históricos são referência, não aprovação de 197 SP |
| Meta Sprint 2 | Campo vazio no Jira; síntese documental pendente de confirmação |
| Extras Sprint 2 | Nenhum explicitamente registrado |
| DoR Sprint 2 | Parcialmente documentado; pendências identificadas |
| Interação com parceiro | Desafio é fonte; ata de validação não identificada |
| Vídeo e aceite integrado | Vincular quando disponíveis; não inferidos dos estados dos tickets |

### Checklist de acompanhamento

- [ ] Product Backlog atualizado e com Rank único.
- [ ] Valor de negócio explícito para todas as histórias.
- [ ] Prioridades coerentes com o Rank.
- [ ] Estimativas revisadas das histórias selecionadas.
- [ ] Sprint Backlog preparado antes da execução.
- [ ] Meta da sprint confirmada e preservada.
- [ ] DoR concluído para as histórias comprometidas.
- [ ] Tasks vinculadas e acompanhadas no Jira.
- [ ] Incremento completo da meta funcionando.
- [ ] Resultado final da sprint preenchido.
- [ ] Vídeo e demais evidências vinculados quando aplicável.

O checklist permanece aberto como acompanhamento da Sprint 2; resultados específicos e limites da consulta estão na tabela acima.

Em cada sprint, manter as estimativas e o Rank atualizados, registrar capacidade e meta, separar extras, vincular evidências do DoR, acompanhar tasks e burndown e preencher o resultado final. Preservar o compromisso e o resultado históricos sem recontar entregas anteriores.

## Páginas relacionadas

- [Backlog da Sprint 1](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/84017153).
- [Backlog da Sprint 2](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/101285889).
- [Relatório consolidado dos backlogs](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/85229570).

## Fontes e rastreabilidade

- Jira Shifu, quadro 331: sprints 497 e 498; consulta de estado em 05/10/2026.
- [Backlog do Produto — Shifu](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83623938), conteúdo 83623938, versão 3; referência histórica de produto.
- [Guia de referência de backlogs — revisão 2025-2](https://drive.google.com/file/d/140xfl-e5tFURvVPsHpNAmW5m1_OQJBNf/view), anexos I e II.
- [Guia de artefatos de requisitos — revisão 2025-2](https://drive.google.com/file/d/1F-3Y3B86-IbT6kDTduXImMN4l2RNolEq/view), seções 1 a 4.

O formato mantém Rank, Prioridade, User Story, Estimativa e Sprint; explicita valor, capacidade, meta, extras e DoR. Jira é a fonte operacional; PRDs são a autoridade de produto. Este relatório não altera tickets, PRDs nem o compromisso configurado.


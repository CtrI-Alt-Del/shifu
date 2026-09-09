<div align="center">
  <h1>Assistente Virtual para Desenvolvimento de Habilidades: Shifu 🥋</h1>
</div>

## 🎯 Descrição do desafio

A GSW é uma empresa de tecnologia que desenvolve soluções corporativas e busca explorar o uso consciente de inteligência artificial aplicada à educação. O desafio consiste em desenvolver um assistente virtual que atue como mentor no desenvolvimento de habilidades, capaz de identificar o nível real de partida do aprendiz, montar uma jornada personalizada, entregar prática com correção e retorno, medir a evolução de forma comprovável e sustentar o engajamento ao longo do tempo. A solução não deve entregar respostas prontas, e sim guiar o usuário até o aprendizado. Duas restrições orientam toda a arquitetura: o consumo de IA precisa ser consciente, definindo explicitamente o que passa pelo modelo e o que é resolvido por lógica própria da aplicação, e o produto não pode deixar de ser útil quando a IA estiver indisponível. O caso funcional de validação do MVP é Lógica de Programação, com atividades práticas de código.

## 📖 Backlog do Produto

| RF | Rank | Prioridade | User story | Estimativa | Sprint |
|-----|------|------------|------------|------------|--------|
| 01 | 1 | Alta | Como usuário, quero criar e confirmar minha conta com nome, e-mail e senha, para que meus dados e experiências permaneçam associados a mim. | – | – |
| 01 | 2 | Alta | Como usuário, quero entrar na aplicação e recuperar meu acesso caso esqueça a senha, para não perder minha jornada de aprendizagem. | – | – |
| 03 | 3 | Alta | Como usuário, quero criar um Objetivo e adicionar Habilidades a ele, para organizar o que pretendo desenvolver. | – | – |
| 03 | 4 | Alta | Como usuário, quero realizar um diagnóstico completo da Habilidade, para descobrir meu ponto de partida sem começar em conteúdo que já domino. | – | – |
| 03 | 5 | Alta | Como usuário, quero acessar materiais de apoio e atividades na ordem definida do conteúdo, para estudar e praticar a Competência atual. | – | – |
| 03 | 6 | Alta | Como usuário, quero enviar respostas de questões objetivas e de código e receber uma avaliação, para saber se minha solução está correta. | – | – |
| 03 | 7 | Alta | Como usuário, quero acompanhar meu progresso e domínio por Competência, para perceber minha evolução real na Habilidade. | – | – |
| 03 | 8 | Alta | Como usuário, quero receber a recomendação da próxima atividade na dificuldade adequada, para saber o que fazer em seguida sem escolher no escuro. | – | – |
| 03 | 9 | Média | Como usuário, quero entender minha nota e o que mudou no meu progresso, para saber exatamente o que preciso melhorar. | – | – |
| 04 | 10 | Média | Como usuário, quero descrever livremente o que desejo aprender e responder perguntas objetivas, para receber uma proposta de Objetivo formada por Habilidades reais do produto. | – | – |
| 04 | 11 | Média | Como usuário, quero conversar com um mentor que conheça meu contexto atual, para receber dicas progressivas sem receber a solução pronta. | – | – |
| 05 | 12 | Média | Como usuário, quero receber XP e subir de nível conforme pratico, para me sentir reconhecido pelo meu esforço. | – | – |
| 05 | 13 | Média | Como usuário, quero manter uma sequência de dias de prática, para sustentar minha constância. | – | – |
| 05 | 14 | Baixa | Como usuário, quero desbloquear conquistas por marcos claros, para ter metas intermediárias visíveis. | – | – |
| 03 | 15 | Baixa | Como usuário, quero consultar o histórico das minhas tentativas e o resumo final de uma Habilidade concluída, para revisar minha trajetória. | – | – |
| 04 | 16 | Baixa | Como usuário, quero saber quanto da minha cota mensal de IA ainda está disponível, para não ser surpreendido por um bloqueio temporário. | – | – |
| 01 | 17 | Baixa | Como usuário, quero excluir minha conta e meus dados associados, para encerrar minha participação no produto. | – | – |

**Legenda dos requisitos funcionais:** `01` Identity · `02` Curriculum · `03` Learning · `04` Intelligence · `05` Gamification

> Estimativas e alocação por sprint são definidas pelo time no planejamento de cada sprint.

---

## 🗓️ Cronograma e Sprints do projeto

| Sprint |    Período da Sprint    |                                       Link para a documentação                                       |      Status      |
| :----: | :---------------------: | :--------------------------------------------------------------------------------------------------: | :-------------: |
|   01   | A definir | [Relatório](https://github.com/CtrI-Alt-Del/shifu/blob/main/documentation/sprints/sprint-1-report.md)  | Não iniciada |
|   02   | A definir | [Relatório](https://github.com/CtrI-Alt-Del/shifu/blob/main/documentation/sprints/sprint-2-report.md)  | Não iniciada |
|   03   | A definir | [Relatório](https://github.com/CtrI-Alt-Del/shifu/blob/main/documentation/sprints/sprint-3-report.md)  | Não iniciada |

## 🛠️ Tecnologias

> A stack ainda está em definição pelo time. Esta seção será preenchida conforme as decisões forem fechadas.

O desafio impõe restrições que orientam a escolha das tecnologias:

- **Uso consciente de IA** → o sistema precisa decidir explicitamente o que é resolvido por lógica própria e o que exige um modelo generativo, medindo e controlando o consumo.

- **Resiliência** → diagnóstico, trilha, prática, correção objetiva, progresso e gamificação precisam continuar funcionando quando a IA estiver indisponível.

- **Processamento de Linguagem Natural** → aplicação de vetorização, embeddings e similaridade semântica pelo próprio time, e não apenas o consumo de uma API de terceiros.

- **Execução de código do usuário** → as atividades práticas de programação são avaliadas por casos de teste, o que exige um ambiente isolado e seguro de execução.

- **Avaliação qualitativa por IA** → critérios definidos previamente no conteúdo, com nota e explicação por critério, sem que a IA decida nota final, progresso ou conclusão.

- **Responsividade e acessibilidade** → todos os fluxos principais precisam funcionar em desktop e mobile, operáveis por teclado, sem depender apenas de cor.

## 📁 Estrutura do Repositório

O projeto está organizado em áreas de produto com responsabilidades bem separadas:

- **Identity**: conta, confirmação de e-mail, acesso, sessões, perfil e exclusão de conta
- **Curriculum**: Habilidades, Competências, materiais de apoio, sequência curricular, atividades e regras de avaliação
- **Learning**: Objetivos, diagnóstico, tentativas, avaliações, progresso, domínio, recomendação e conclusão
- **Intelligence**: Mentor contextual, Planejador de Objetivos e controle da cota de IA
- **Gamification**: XP, nível, sequência, conquistas, calendário de atividade e histórico de recompensas

Arquivos atuais do repositório:

- **`design.md`**: design system e especificação das telas, base para a construção do design no Pencil
- **`documentation/`**: documentação técnica e relatórios de progresso do projeto

> A divisão em repositórios de aplicação segue o padrão da organização e será definida junto com a stack.

## ▶️ Como executar o projeto

O projeto ainda não possui aplicação executável. As instruções de execução serão publicadas no **`readme.md`** de cada repositório de aplicação assim que a stack for definida.

## 🎥 Demonstração em Vídeo

- A publicar ao final da primeira sprint

## 📚 Links Úteis

- [PRDs do produto](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/82804737/PRD+s)
- [Design System e Especificação de Telas](https://github.com/CtrI-Alt-Del/shifu/blob/main/design.md)
- [DoR (Definition of Ready)](https://github.com/CtrI-Alt-Del/shifu/blob/main/documentation/dor.md)
- [DoD (Definition of Done)](https://github.com/CtrI-Alt-Del/shifu/blob/main/documentation/dod.md)
- [Estratégia de branches](https://github.com/CtrI-Alt-Del/shifu/blob/main/documentation/branch-strategy.md)
- [Padrão de commit](https://github.com/CtrI-Alt-Del/shifu/blob/main/documentation/commit-pattern.md)

## 👷🏻 Equipe

|                                    Foto                                    |          Nome           |    Função     |                                                                            Github                                                                            |                                                                                              Linkedin                                                                                               |
| :------------------------------------------------------------------------: | :---------------------: | :-----------: | :----------------------------------------------------------------------------------------------------------------------------------------------------------: | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
|       <img src="https://github.com/Tico1606.png?size=50" width="50">       |    Gabriel Oliveira     | Scrum Master  |       <a href="https://github.com/Tico1606"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white"></a>       |          <a href="https://www.linkedin.com/in/gabriel-oliveira-884ba5282/"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white"></a>           |
|  <img src="https://github.com/JoaoGabrielGarcia.png?size=50" width="50">   |  Joao Gabriel Oliveira  | Product Owner |  <a href="https://github.com/JoaoGabrielGarcia"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white"></a>   |  <a href="https://www.linkedin.com/in/jo%C3%A3o-gabriel-oliveira-garcia-b2563a22a/"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white"></a>  |
|      <img src="https://github.com/JohnPetros.png?size=50" width="50">      |   Joao Pedro Carvalho   |   Dev Team    |      <a href="https://github.com/JohnPetros"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white"></a>      | <a href="https://www.linkedin.com/in/jo%C3%A3o-pedro-carvalho-dos-santos-42a0ab222/"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white"></a> |
|        <img src="https://github.com/kaufon.png?size=50" width="50">        |  Kauan Fonseca do Vale  |   Dev Team    |        <a href="https://github.com/kaufon"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white"></a>        |            <a href="https://www.linkedin.com/in/kauan-fonseca-b62188300/"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white"></a>            |
|        <img src="https://github.com/0thigs.png?size=50" width="50">        |     Thiago Martins      |   Dev Team    |        <a href="https://github.com/0thigs"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white"></a>        |            <a href="https://www.linkedin.com/in/thiago-martins-fullstack/"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white"></a>             |

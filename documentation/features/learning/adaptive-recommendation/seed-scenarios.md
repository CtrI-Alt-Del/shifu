# Laboratório local da recomendação adaptativa

A seed de desenvolvimento inclui a Habilidade **Laboratório de decisões adaptativas**
e o Objetivo **Laboratório de progresso adaptativo** na conta local descrita em
[`documentation/tooling.md`](../../../tooling.md). O Objetivo começa sem diagnóstico
ou progresso v2. Sua Habilidade usa duas Competências: **Interpretar condições**
contém os Conceitos **Condições e limites** e **Combinação e negação**; **Resolver
prioridades** contém **Prioridades e exceções**. Cada Conceito tem um Material,
três Atividades diagnósticas (fácil, média e difícil) e seis Atividades de
aprendizagem (duas por dificuldade). Os pré-requisitos formam uma cadeia entre os
três Conceitos, e as Atividades de aprendizagem exigem que a base esteja
suficientemente demonstrada. As questões têm
respostas corretas e incorretas explícitas para permitir progresso e regressão reais.

Use o comando `db:seed` somente em uma base **local descartável**: ele apaga os dados
de aplicação existentes, inclusive progresso e eventos pendentes do percurso anterior.
A seed não é executada na inicialização. Após aplicar as
migrações e executar o comando documentado em `documentation/tooling.md`, entre na
conta local, abra o Objetivo do laboratório e inicie a Habilidade. A página de
diagnóstico apresenta nove Atividades em ordem: fácil, média e difícil de cada um
dos dois Conceitos de condições, depois fácil, média e difícil de prioridades.
As respostas individuais do diagnóstico
não ficam visíveis; ao fim, aparece o resumo consolidado.

Para conferir os formatos de questão, a primeira Atividade diagnóstica
(`01SHF000000000000000000052`) contém uma questão de **escolha única** sobre um
trecho Python em Markdown. A quarta (`01SHF000000000000000000076`) contém
**múltipla seleção** sobre pessoas que satisfazem uma conjunção; as respostas
corretas são Ana e Cris. Na aprendizagem, **Duas exigências**
(`01SHF000000000000000000079`) combina múltipla seleção, trecho Python em
Markdown e duas questões de escolha única. Nessa primeira questão, a seleção
correta é `tem_cracha é True` e `pode_entrar é False`. A URL de cada Atividade
usa `/learning/goals/01SHF000000000000000000070/skills/01SHF000000000000000000045/competencies/01SHF000000000000000000046/activities/<ID>`.
As rotas só abrem quando a Habilidade já foi iniciada e a etapa permite acessar
a Atividade; siga o diagnóstico pelo Objetivo para chegar nelas.

Para percorrer um cenário de progresso claro:

1. Erre as seis questões diagnósticas de **Interpretar condições**. Acerte as duas
   primeiras de **Resolver prioridades** e erre a última. Os dois primeiros
   Conceitos partem de progresso diagnóstico zero; o Material do alvo aparece
   como apoio opcional junto de uma Atividade fácil.
2. Siga as recomendações e acerte as Atividades de aprendizagem da primeira
   Competência. Observe a troca de foco entre seus Conceitos, a cobertura das
   três dificuldades e a subida do progresso até o domínio, sustentado por
   Atividades distintas e evidências difíceis. O resumo diagnóstico continua
   com a linha de base original.
3. Abra **Resolver prioridades**. A Competência agora está disponível e recebe
   recomendação própria. Respostas certas e erradas nas suas Atividades permitem
   observar como a recomendação escolhe dificuldade, reforço e Material.
4. Antes de concluir a Habilidade, para observar uma piora, refaça duas Atividades
   distintas da primeira Competência já dominada com respostas erradas. Compare o
   resultado da tentativa com progresso, verificação e recomendação; conteúdo já
   liberado não deve voltar a bloquear.

Para testar uma trajetória diferente sem apagar dados, crie outro Objetivo com a
mesma Habilidade. O Objetivo pronto na seed serve como ponto de partida, enquanto
novos Objetivos mantêm trajetórias independentes. A Habilidade menor **Decisões em
algoritmos** continua disponível para inspecionar o caminho v2 de um único Conceito;
as Habilidades legadas continuam v1.

O cenário acima é reproduzido até a liberação da segunda Competência pelo teste
HTTP/PostgreSQL em
`apps/server/tests/learning/server/controllers/test_adaptive_journey_controller.py`.
Regressão após domínio e outras trajetórias também têm testes da política, mas o
roteiro manual completo não substitui uma avaliação de eficácia com alunos ou
questões inéditas.

Como o diagnóstico de escolha produz evidência válida para todos os Conceitos
publicados, este laboratório mostra a oferta de Material por **progresso baixo**.
A regra de Material opcional quando ainda não existe observação válida é exercitada
pelos testes unitários da política; ela não aparece naturalmente após completar
este diagnóstico.

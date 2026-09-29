# Roteiro da demonstração: Lógica de programação

Use uma experiência **não iniciada** da habilidade Lógica de programação. O diagnóstico inicial tem uma sequência fixa de **oito questões**, uma por atividade, sem ramificações. Prepare o resultado antes da apresentação para concentrar a demonstração no ponto de partida, na atividade e no progresso.

No objetivo **Aprender a programar**, mostre primeiro o grafo com cinco Habilidades: Lógica de programação, JavaScript essencial, HTML e CSS, React e APIs web. As últimas quatro são nós ilustrativos, sem Competências ou questões; abra **Lógica de programação** para demonstrar o diagnóstico e a prática.

## Respostas do diagnóstico

Cada questão tem quatro alternativas. As questões 4 e 7 permitem selecionar **duas respostas corretas**; as outras pedem uma resposta. Responda corretamente a sete questões. Na competência **Decisões**, erre somente esta:

| Atividade | Questão | Resposta a selecionar | Resposta correta |
| --- | --- | --- | --- |
| Diagnóstico: escolher o ramo (média) | `n=0` em `se n < 0 imprime N; senão Z` | `N` | `Z` |

Na questão 4, selecione `2 + 3 * 4` e `2 * (3 + 4)`. Na questão 5, selecione `n === 0`. Na questão 7, selecione “O corpo executa 3 vezes” e “Ao final, n vale 3”. Assim, o diagnóstico observa uma comparação correta e dificuldade em escolher o ramo para zero.

Depois de concluir o diagnóstico e aguardar a avaliação, confira:

1. **Decisões** é a competência em foco.
2. A recomendação indica **Decisão condicional** como conceito em foco. Seu ponto de partida fica em 0%, enquanto **Comparações e limites** fica em 100%.
3. A primeira atividade recomendada é **Classificar um número**, de dificuldade fácil.
4. **Ler material de apoio** abre **Introdução: Decisões** como opção antes da prática.
5. **Continuar praticando** abre a atividade com a questão editável `classificarNumero(numero)`.

Os conceitos não avaliados permanecem **sem evidência** e a competência não é marcada como dominada. As respostas corretas anteriores permitem chegar provisoriamente a Decisões; a resposta errada faz dela o foco de prática.

Na questão de código, uma solução possível é:

```javascript
function classificarNumero(numero) {
  if (numero > 0) return 'positivo'
  if (numero < 0) return 'negativo'
  return 'zero'
}

for (const numero of [5, -3, 0]) console.log(classificarNumero(numero))
```

A saída esperada é `positivo`, `negativo`, `zero`, em linhas separadas. O teste `TestLogicProgrammingSeed::test_diagnostic_evidence_leads_to_progress_or_completion[classify]` reproduz o diagnóstico pela API com PostgreSQL descartável e verifica a recomendação e a abertura da atividade. O resultado oficial da questão de código depende da avaliação configurada no ambiente da apresentação.

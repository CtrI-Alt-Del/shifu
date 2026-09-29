# Simulação matemática do progresso e da recomendação

> Material para apresentação. Todos os valores e identificadores M1–M2 e H1–H3
> abaixo são **hipotéticos**. Nenhuma Atividade precisa ser cadastrada ou executada
> no Shifu para reproduzir os cálculos deste relatório.

## Fonte e alcance

Esta projeção aplica o [PRD canônico de Learning](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDzB),
conteúdo `83066881`, versão 24, consultado em 28/09/2026, especialmente RP-07,
RP-15, RP-16 e RP-17. Os números representam **evidências válidas de um Conceito**;
não representam necessariamente a nota total de uma Atividade. Para permitir a
ilustração do domínio, a Competência hipotética possui apenas esse Conceito.

O relatório projeta progresso, condições de domínio e dificuldade indicada pela
política. A escolha de uma Atividade específica exige um catálogo real com
mapeamento de Conceitos, disponibilidade, pré-requisitos e avaliação confiável;
por isso, nenhum título ou identificador real é previsto aqui.

## Regras matemáticas usadas

Se houver observações diagnósticas válidas nas três dificuldades, a base do
Conceito é a média das médias por dificuldade:

```text
base = (média_fácil + média_média + média_difícil) / 3
```

Uma dificuldade sem observação válida não entra como zero. A base então é
parcial, e a cobertura continua incompleta. Para cada Atividade de aprendizagem
distinta com evidência válida `x`, na ordem do primeiro envio:

```text
novo_progresso = 0,7 × progresso_anterior + 0,3 × x
```

Quando uma Atividade é refeita, sua nova evidência válida **substitui** a
contribuição anterior na posição original. O progresso é recalculado desde a
base. Uma evidência inconclusiva preserva a contribuição válida anterior e
abre verificação; não equivale a zero.

### Ausência de evidência versus evidência zero

| Diagnóstico fácil | Médio | Difícil | Base | Cobertura |
| ---: | ---: | ---: | ---: | --- |
| 50 | 50 | Inconclusivo | 50 | Parcial: falta evidência difícil |
| 50 | 50 | 0 | 33,333… | Completa nas três dificuldades |

O primeiro caso não autoriza concluir domínio, mesmo que o progresso numérico
suba posteriormente, até que a dificuldade ausente receba uma observação válida.

## Cenário principal: evolução de um Conceito

Premissas: as três observações diagnósticas são válidas e valem 50; portanto,
a base é 50 e há cobertura fácil, média e difícil. Cada linha seguinte é uma
nova Atividade hipotética, distinta, com evidência válida para o mesmo Conceito.
Não há avaliação pendente nem verificação inconclusiva. Admitimos que o
Currículo hipotético ofereça uma candidata executável em cada dificuldade
indicada.

| Momento | Evidência do Conceito | Cálculo | Progresso | Estado da Competência* | Dificuldade indicada a seguir |
| --- | ---: | --- | ---: | --- | --- |
| Fim do diagnóstico | Base 50 | `(50 + 50 + 50) / 3` | 50 | Em desenvolvimento | Média |
| M1, média | 80 | `0,7 × 50 + 0,3 × 80` | 59 | Em desenvolvimento | Média |
| M2, média | 90 | `0,7 × 59 + 0,3 × 90` | 68,3 | Em desenvolvimento | Difícil |
| H1, difícil | 100 | `0,7 × 68,3 + 0,3 × 100` | 77,81 | Proficiente | Difícil |
| H2, difícil | 100 | `0,7 × 77,81 + 0,3 × 100` | 84,467 | Proficiente | Difícil, se houver candidata útil |
| H3, difícil | 100 | `0,7 × 84,467 + 0,3 × 100` | 89,1269 | Dominada | Próxima Competência, se houver; senão, resumo final |

\* O estado é ilustrativo para uma Competência com **um único Conceito**.

Após M2, duas Atividades médias distintas têm evidência vigente de pelo menos
80. A política permite recomendar dificuldade difícil apesar de o progresso
ainda estar abaixo de 70. Após H1, já existe confirmação difícil de pelo
menos 80, mas o progresso ainda não atinge 85. Após H3, as condições de entrada
em domínio estão atendidas no cenário: média completa ≥ 85, progresso do único
Conceito ≥ 70, atividades distintas, evidência nas três dificuldades,
confirmação difícil ≥ 80 e nenhuma verificação pendente.

A tabela indica **necessidade e dificuldade**, não uma Atividade garantida.
Se H3 não existir ou não puder ser avaliada, o algoritmo precisa procurar outra
candidata útil ou informar a lacuna; não pode inventá-la.

### Quanto falta para atingir 85?

Com progresso atual `p`, uma nova contribuição válida `x` levaria o Conceito
ao limiar numérico de 85 quando:

```text
x ≥ (85 − 0,7 × p) / 0,3
```

Depois de H2, `p = 84,467`, então `x ≥ 86,243…`. Evidência 100 em H3 supera
esse limiar. A desigualdade considera somente o número: cobertura,
diversidade, confirmação difícil e verificação continuam sendo condições
separadas de domínio.

## Cenário de retentativa: substituição sem ganho fictício

Considere base 50 e duas Atividades distintas, A e B, enviadas nessa ordem:

| Evidências vigentes | Cálculo a partir da base | Progresso |
| --- | --- | ---: |
| A = 0; B = 100 | `0,7 × (0,7 × 50 + 0,3 × 0) + 0,3 × 100` | 54,5 |
| A refeita com 10; B = 100 | `0,7 × (0,7 × 50 + 0,3 × 10) + 0,3 × 100` | 56,6 |

A retentativa melhora A de 0 para 10, mas não cria uma terceira contribuição
nem muda sua ordem. Essa distinção evita inflar progresso e diversidade pelo
simples número de tentativas.

## Projeção com resultados constantes

Se a base é `b` e cada uma das `n` Atividades distintas seguintes fornece a
mesma evidência `x`, a recorrência resulta em:

```text
progresso_n = x + (b − x) × 0,7^n
```

Para `b = 50` e `x = 100`, a sequência é 65; 75,5; 82,85; 87,995.
São necessárias **quatro contribuições distintas de 100** para ultrapassar 85
nesse caso. Se `x = 80`, a sequência se aproxima de 80 e nunca alcança 85.
Em ambos os casos, atingir o limiar numérico não dispensa as demais condições
de domínio.

## Como apresentar e interpretar

1. Mostre a origem da base diagnóstica e a diferença entre evidência ausente e zero.
2. Acompanhe uma linha da tabela por vez: evidência, cálculo, progresso e necessidade seguinte.
3. Destaque a promoção para dificuldade difícil após duas evidências médias fortes.
4. Use a retentativa para demonstrar recomputação em posição estável.
5. Separe o limiar numérico das demais condições de domínio.

Esta é uma **projeção da política definida**, não uma previsão de nota futura
de um aprendiz, uma medição de eficácia pedagógica ou um teste de ponta a ponta
do software. Os parâmetros 70/30 e os limiares pertencem ao MVP e exigem
validação posterior com conteúdo real, tarefas novas e retenção da aprendizagem.

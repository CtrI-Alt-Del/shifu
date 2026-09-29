# Verificação do algoritmo adaptativo de Learning

Data: 28/09/2026. Referência de produto: [PRD canônico de Learning](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDzB), conteúdo `83066881`, versão 24, especialmente RP-15, RP-16 e RP-17. Esta verificação examina a política que estava no diretório de trabalho nessa data; o arquivo da política contém alterações locais ainda não integradas.

## Alcance e método

Três revisões independentes examinaram (1) a [simulação matemática](progress-mathematical-simulation.md), (2) a conformidade entre PRD e `AdaptiveLearningPolicy.evaluate` e (3) o custo computacional da recomendação. Os cenários de divergência e o benchmark chamaram a política diretamente com dados artificiais em memória. A verificação inicial não criou Atividades no produto nem alterou banco, serviços ou código do algoritmo. As correções posteriores alteraram somente a política e seus testes.

Foram executados, em `apps/server`:

```sh
uv run pytest tests/learning/core/domain/test_adaptive_learning_policy.py -q
uv run pytest tests/learning/core/use_cases -q
uv run pytest tests/learning/core -q
uv run poe check:lint
uv run poe check:types
uv run poe check:architecture
```

Resultados da verificação inicial: **15/15 testes da política** e **111/111 testes dos casos de uso de Learning** passaram. Após as três correções descritas abaixo, **130/130 testes de Learning core** passaram, incluindo os 19 testes da política; lint, arquitetura e verificação de tipos do servidor também passaram. A simulação foi recalculada independentemente com `Decimal`: `50 → 59 → 68,3 → 77,81 → 84,467 → 89,1269`; limiar da próxima evidência após H2 `86,243…`; retentativa `54,5 → 56,6`. Os estados e dificuldades desse cenário hipotético são coerentes com a implementação atual.

## Achados reproduzidos frente a RP-17

| Caso | Entrada e resultado observado na verificação inicial | Resultado exigido pela regra | Situação local |
| --- | --- | --- | --- |
| Consolidação | Diagnóstico fácil `0`, médio `50`, difícil `100` dá base `50`. Aprendizagem `e-old` fácil `0` e `m-old` médio `100` dá progresso `54,5`. Sem candidata média útil, a política escolhia `e-new` fácil. Sua melhora hipotética é `13,65`, enquanto refazer `e-old` poderia melhorar `21`. | Na consolidação, priorizar o **maior ganho positivo** entre candidatas até a dificuldade preferida. | **Corrigido no diretório de trabalho**: agora escolhe `e-old`; dois testes cobrem ganho maior e ausência de retentativa útil. |
| Regressão da média | Dois Conceitos `a` e `b` ficam em `70` após domínio prévio. A atividade de `a` está indisponível e a de `b` disponível. Com `a` primeiro na ordem curricular, a política informava `curriculum_or_assessment_unavailable`; ao inverter só as posições, recomendava `b`. | Escolher o Conceito de menor progresso **com ação relevante viável** antes de declarar lacuna. | **Corrigido no diretório de trabalho**: a seleção procura a primeira ação viável na ordem de menor progresso e recomenda `b` nesse caso. |
| Permissão de dificuldade | Duas evidências fáceis `80` autorizam dificuldade média. Após retentativa inconclusiva de uma delas, o progresso válido anterior é preservado, mas a política continuava recomendando média com base nas duas evidências. | Suspender o uso da evidência sob verificação para a permissão de subir a dificuldade até esclarecê-la. | **Corrigido no diretório de trabalho**: a permissão usa só evidências não suspensas; a recomendação volta a fácil até a verificação ser esclarecida. |

Os três casos foram reproduzidos antes das correções e cobertos por testes que passam depois delas. As mudanças dizem respeito à **seleção da próxima ação**; preservam os cálculos 70/30 do cenário principal da simulação.

## Custo de execução

Benchmark artificial **anterior à correção de consolidação**, em memória: cinco execuções para os cenários com 500 observações e três para o replay após domínio; os valores são medianas de `evaluate` e não representam a latência atual após a mudança:

| Cenário | Mediana |
| --- | ---: |
| 5 Atividades e 500 observações | `10,75 ms` |
| 20 Atividades e 500 observações | `46,80 ms` |
| 200 observações após domínio, com replay de regressão | `24,12 ms` |

No cenário anterior de 20 Atividades e 500 observações, a política calculou `_potential_gain` **40 vezes**: a busca de consolidação e a ordenação recalculavam o ganho das mesmas candidatas. A correção agora reutiliza cada ganho dentro da seleção de uma Atividade. A verificação de regressão ainda recompõe prefixos sucessivos do histórico, o que pode crescer aproximadamente de forma quadrática no número de observações relevantes. A busca do detalhe de Competência calcula a política dentro de uma transação de leitura, e o repositório carrega todo o histórico da experiência. Isso é um risco de latência e concorrência; os números acima **não** incluem banco, serialização, múltiplas requisições ou catálogo real e **não** são um SLA.

## Conclusão para a apresentação

A projeção matemática está validada como **exemplo da política**. Os três desvios de seleção encontrados nesta auditoria foram corrigidos no diretório de trabalho e têm testes de regressão. A apresentação pode demonstrar a fórmula, a substituição de retentativas e os critérios de domínio. Os testes focados não comprovam, por si, conformidade completa de todos os cenários, desempenho com banco real ou eficácia pedagógica.

Próximas verificações úteis: medir latência p95 com catálogo e banco reais e avaliar resultados de aprendizagem antes de afirmar ganho pedagógico.

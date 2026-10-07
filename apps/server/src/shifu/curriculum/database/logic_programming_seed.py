"""Deterministic development curriculum for the Logic Programming skill.

Construction is pure. The shared seed entrypoint decides when to persist it.
"""

from dataclasses import dataclass

from shifu.curriculum.core.domain.entities import (
    Activity,
    Competency,
    Concept,
    Material,
    Skill,
)
from shifu.curriculum.core.domain.enums import (
    ActivityDifficulty,
    ActivityType,
    MaterialType,
)
from shifu.curriculum.core.domain.structures import (
    ActivitySequenceItem,
    ChoiceConceptCriterion,
    ChoiceOption,
    CodeConceptCriterion,
    CodeInconclusiveComment,
    CodeInconclusiveObservation,
    CodeLevelObservation,
    CodeRubricComment,
    CodeRubricCriterion,
    CodeRubricEvaluationPart,
    CorrectnessEvaluationPart,
    CurriculumSequence,
    EvaluationRule,
    JavascriptInitialFile,
    JavascriptPermittedCommand,
    JavascriptStdinQuestion,
    MaterialSequenceItem,
    MultipleSelectionQuestion,
    SingleChoiceQuestion,
)
from shifu.shared.core.domain.structures import structure


LOGIC_SKILL_ID = '01SHF000000000000000000002'
LOGIC_DECISIONS_COMPETENCY_ID = '01SHF000000000000000000312'
LOGIC_CLASSIFY_ACTIVITY_ID = '01SHF000000000000000000410'


def _id(number: int) -> str:
    return f'01SHF000000000000000000{number:03d}'


LOGIC_INITIAL_DIAGNOSTIC_ACTIVITY_IDS = tuple(_id(430 + index) for index in range(8))


@structure
class LogicProgrammingSeed:
    skill: Skill
    competencies: tuple[Competency, ...]
    concepts: tuple[Concept, ...]
    materials: tuple[Material, ...]
    activities: tuple[Activity, ...]
    curriculum_sequences: tuple[CurriculumSequence, ...]


@dataclass(frozen=True, slots=True)
class _ConceptContent:
    name: str
    description: str
    observation: str
    # Nine observable, distinct cases: three diagnostic, then six learning.
    cases: tuple[tuple[str, str, str], ...]


@structure
class _GroupContent:
    competency_index: int
    concepts: tuple[_ConceptContent, ...]
    diagnostic_titles: tuple[str, str, str]
    learning_titles: tuple[str, str, str, str, str, str]


@dataclass(frozen=True, slots=True)
class _MultipleSelectionCase:
    prompt: str
    options: tuple[tuple[str, bool], ...]


_COMPETENCIES = (
    (
        'Sequência de instruções',
        'Execute instruções em ordem, leia entradas e acompanhe as saídas.',
        (
            'Um algoritmo é uma sequência de passos. Em um programa simples, cada '
            'instrução é executada na ordem em que aparece: primeiro recebemos dados, '
            'depois os transformamos e, por fim, apresentamos uma saída. Trocar a '
            'ordem dos passos pode mudar o resultado.\n\n'
            'Acompanhe o valor das variáveis depois de cada linha, sem pular direto '
            'para a resposta. No exemplo, `total` começa em 2, passa a valer 5 e '
            'somente então é mostrado no console.\n\n'
            '```javascript\nlet total = 2;\ntotal = total + 3;\nconsole.log(total); // 5\n```\n\n'
            'Para rastrear um programa, faça uma tabela com uma linha por instrução: '
            'instrução executada, valor anterior, valor novo e saída produzida. '
            'Uma atribuição posterior não altera retroativamente um valor já '
            'copiado para outra variável.\n\n'
            'Experimente prever a saída de `let x = 4; let y = x; x = 9; '
            'console.log(y);`. O resultado é `4`: `y` recebeu o valor que `x` '
            'tinha no momento da atribuição. Depois, troque a ordem das duas '
            'atribuições e compare.'
        ),
    ),
    (
        'Variáveis e expressões',
        'Guarde, atualize e combine valores em expressões.',
        (
            'Uma variável guarda um valor que pode ser consultado e atualizado. '
            'Em `let pontos = 4`, o nome é `pontos` e o valor inicial é 4. '
            'A instrução `pontos = pontos + 2` lê o valor antigo, soma 2 e '
            'guarda 6. O sinal `=` faz uma atribuição; não afirma que os dois '
            'lados são iguais para sempre.\n\n'
            '```javascript\nlet pontos = 4;\npontos = pontos + 2;\nconsole.log(pontos); // 6\n```\n\n'
            'Uma expressão combina valores com operadores. Multiplicação e divisão '
            'são resolvidas antes de adição e subtração; parênteses mudam essa '
            'ordem. Por isso, `2 + 3 * 4` resulta em 14, enquanto '
            '`(2 + 3) * 4` resulta em 20.\n\n'
            'Para conferir uma expressão, resolva primeiro os parênteses, depois '
            'multiplicações e divisões e, por último, somas e subtrações. '
            'Ao atualizar uma variável, use o valor que ela possui naquele passo, '
            'não seu valor inicial. Teste: `let n = 3; n = n * 2; n = n + 1;`. '
            'O valor final é `7`.'
        ),
    ),
    (
        'Decisões',
        'Escolha caminhos com comparações, condições e operadores booleanos.',
        (
            'Uma comparação responde `true` ou `false`. Use `>`, `<` e `===` '
            'para verificar se um número é maior, menor ou igual a outro. '
            'O limite entre positivos e negativos é zero: ele não pertence a '
            'nenhum dos dois grupos.\n\n'
            '`if` executa um bloco quando sua condição é verdadeira. Se ela for '
            'falsa, o programa pode testar um `else if`; se nenhum teste passar, '
            'executa o `else`. Nessa cadeia, apenas um ramo é escolhido.\n\n'
            '```javascript\nfunction classificarNumero(n) {\n  if (n > 0) {\n    return "positivo";\n  } else if (n < 0) {\n    return "negativo";\n  }\n  return "zero";\n}\n```\n\n'
            'Teste os três caminhos com `5`, `-3` e `0`. Testar apenas valores '
            'positivos não revela um erro no ramo negativo ou no caso limite. '
            'A ordem dos testes também importa: uma condição ampla antes de '
            'uma condição específica pode impedir que a segunda seja alcançada.\n\n'
            'Para combinar condições, `&&` exige que ambas sejam verdadeiras, '
            '`||` exige pelo menos uma e `!` inverte o resultado lógico. '
            'Por exemplo, `idade >= 18 && idade < 60` descreve uma faixa; '
            'verifique os limites `17`, `18`, `59` e `60`.'
        ),
    ),
    (
        'Repetição',
        'Repita passos e determine quando parar.',
        (
            'Uma repetição executa o mesmo bloco enquanto houver trabalho a '
            'fazer. Use `for` quando a contagem de passos está clara. No exemplo, '
            '`i` começa em 0, o bloco roda enquanto `i < 3` e `i++` aumenta '
            'o contador depois de cada passagem.\n\n'
            '```javascript\nfor (let i = 0; i < 3; i++) {\n  console.log(i);\n}\n// Saída: 0, 1, 2\n```\n\n'
            'Use `while` quando a parada depende do estado. A condição é '
            'verificada antes de cada passagem. Se começar falsa, o corpo não '
            'executa nenhuma vez. Dentro do corpo, atualize algo que permita '
            'chegar à parada; caso contrário, a repetição pode não terminar.\n\n'
            '```javascript\nlet n = 0;\nwhile (n < 3) {\n  n++;\n}\nconsole.log(n); // 3\n```\n\n'
            'Para rastrear o laço, anote em cada passagem o valor de `n` antes '
            'do teste e depois da atualização. Aqui o corpo executa três vezes '
            'e termina com `n` igual a 3. Experimente começar com `n = 3`: '
            'o corpo executa zero vezes.'
        ),
    ),
    (
        'Decomposição em funções',
        'Separe o problema em etapas e passe dados entre funções.',
        (
            'Decompor um problema é separar passos com responsabilidades claras. '
            'Uma função dá nome a um desses passos e permite reutilizá-lo. '
            'O parâmetro é o nome usado dentro da função; o argumento é o valor '
            'passado na chamada. `return` devolve um resultado para quem chamou.\n\n'
            '```javascript\nfunction dobrar(x) {\n  return x * 2;\n}\nconst resultado = dobrar(4);\nconsole.log(resultado); // 8\n```\n\n'
            'Nesse exemplo, `x` é o parâmetro, `4` é o argumento e `8` é o '
            'valor retornado. A função calcula; `console.log` apresenta. '
            'Sem `return`, quem chama a função não recebe o valor calculado.\n\n'
            'Para um problema maior, separe entrada, transformação e saída. '
            'Na classificação de números, uma função pode receber `n` e '
            'devolver `"positivo"`, `"negativo"` ou `"zero"`; outra parte '
            'do programa decide como exibir esse texto. Assim, é possível '
            'testar a regra com `5`, `-3` e `0` sem depender da apresentação.\n\n'
            'Ao ler uma função, identifique o que ela recebe, quais decisões '
            'toma e o que devolve. Se ela mistura várias tarefas sem necessidade, '
            'considere dividir a solução em etapas menores.'
        ),
    ),
)


_GROUPS = (
    _GroupContent(
        competency_index=0,
        concepts=(
            _ConceptContent(
                'Ordem de execução',
                'A ordem altera o estado e a saída.',
                'Determina o resultado de instruções executadas em sequência.',
                (
                    ('`x = 2; x = x + 1;` Qual é x?', '3', '2'),
                    ('`x = 5; x = 2;` Qual é x?', '2', '5'),
                    ('`x = 1; x = x * 2; x = x + 3;` Qual é x?', '5', '8'),
                    ('`saldo = 10; saldo = saldo - 4;` Qual é saldo?', '6', '14'),
                    ('`a = 2; b = a + 1; a = 9;` Qual é b?', '3', '10'),
                    ('`n = 3; n = n + 2; n = n * 2;` Qual é n?', '10', '12'),
                    (
                        '`total = 0; total = total + 4; total = total + 7;` Qual é total?',
                        '11',
                        '7',
                    ),
                    ('`x = 8; y = x; x = 1;` Qual é y?', '8', '1'),
                    ('`x = 2; x = x * 3; x = x - 1;` Qual é x?', '5', '3'),
                ),
            ),
            _ConceptContent(
                'Entrada e saída',
                'Identificar dados lidos e valores apresentados.',
                'Distingue entrada, transformação e saída observável.',
                (
                    (
                        '`nome = entrada; mostrar(nome)`. O que é mostrado?',
                        'O valor recebido',
                        'O texto entrada',
                    ),
                    ('`idade = 20; mostrar(idade + 1)`. Qual é a saída?', '21', '20'),
                    ('Lê 4 e mostra o dobro. Qual é a saída?', '8', '4'),
                    ('Recebe preço 12 e mostra preço + 3. Qual é a saída?', '15', '12'),
                    (
                        'Recebe o texto `Ana` e mostra `Olá, ` + nome. Qual é a saída?',
                        'Olá, Ana',
                        'Olá, nome',
                    ),
                    ('Recebe 7 e 2 e mostra a diferença. Qual é a saída?', '5', '9'),
                    ('Recebe 3 e mostra três vezes o valor. Qual é a saída?', '9', '3'),
                    ('Recebe 0 e mostra valor + 5. Qual é a saída?', '5', '0'),
                    ('Recebe 10 e 4 e mostra a soma. Qual é a saída?', '14', '6'),
                ),
            ),
            _ConceptContent(
                'Rastreamento de valores',
                'Acompanhar valores intermediários.',
                'Reconstrói o estado após cada etapa sem confundir valores anteriores.',
                (
                    ('Começa em 1, soma 2 e dobra. Qual é o valor final?', '6', '4'),
                    (
                        'Começa em 8, subtrai 3 e soma 1. Qual é o valor final?',
                        '6',
                        '4',
                    ),
                    (
                        'Começa em 2, dobra e triplica. Qual é o valor final?',
                        '12',
                        '10',
                    ),
                    (
                        'Pontos: 4, depois +3, depois -2. Quantos pontos restam?',
                        '5',
                        '9',
                    ),
                    ('Estoque: 9, vende 2, repõe 5. Quantos itens restam?', '12', '2'),
                    ('Saldo: 20, paga 8, recebe 3. Qual é o saldo?', '15', '9'),
                    ('Contador: 0, +1, +1, +1. Qual é o valor final?', '3', '1'),
                    ('Pontuação: 2, triplica, perde 1. Qual é o final?', '5', '3'),
                    ('Distância: 5, dobra, soma 4. Qual é o final?', '14', '18'),
                ),
            ),
        ),
        diagnostic_titles=(
            'Diagnóstico: ordem e entrada',
            'Diagnóstico: transformações',
            'Diagnóstico: rastrear etapas',
        ),
        learning_titles=(
            'Instruções em sequência',
            'Entrada para saída',
            'Estado intermediário',
            'Percurso de valores',
            'Auditoria da sequência',
            'Desafio de rastreamento',
        ),
    ),
    _GroupContent(
        competency_index=1,
        concepts=(
            _ConceptContent(
                'Atribuição',
                'Guardar um valor em uma variável.',
                'Identifica qual valor uma variável recebe.',
                (
                    ('`let cor = "azul"`. Qual valor está em cor?', 'azul', 'cor'),
                    ('`let total = 7`. Qual valor está em total?', '7', '0'),
                    ('`let ativo = true`. Qual valor está em ativo?', 'true', 'false'),
                    ('`let pedido = 12`. Qual é o valor de pedido?', '12', 'pedido'),
                    (
                        '`let nome = "Lia"; let apelido = nome`. Qual texto foi atribuído a apelido?',
                        'Lia',
                        'nome',
                    ),
                    ('`let quantidade = 0`. Qual valor foi atribuído?', '0', '1'),
                    ('`let base = 4; let copia = base`. Qual é copia?', '4', 'base'),
                    ('`let preco = 19`. Qual é preco?', '19', '0'),
                    (
                        '`let inicial = false; let aprovado = inicial; inicial = true`. Qual é aprovado?',
                        'false',
                        'true',
                    ),
                ),
            ),
            _ConceptContent(
                'Atualização de valores',
                'Substituir o estado anterior pelo resultado novo.',
                'Calcula corretamente o novo valor após uma atribuição.',
                (
                    ('`x = 3; x = x + 1`. Qual é x?', '4', '3'),
                    ('`p = 8; p = p - 2`. Qual é p?', '6', '10'),
                    ('`n = 2; n = n * 3`. Qual é n?', '6', '5'),
                    (
                        'Caixa começa em 5 e recebe mais 4. Qual é o novo total?',
                        '9',
                        '5',
                    ),
                    (
                        'Estoque começa em 12 e vende 3. Qual é o novo estoque?',
                        '9',
                        '15',
                    ),
                    (
                        'Pontuação começa em 7 e dobra. Qual é a nova pontuação?',
                        '14',
                        '9',
                    ),
                    ('`valor = 1; valor += 5`. Qual é valor?', '6', '5'),
                    (
                        '`tentativas = 4; tentativas -= 1; tentativas += 2`. Qual é tentativas?',
                        '5',
                        '3',
                    ),
                    (
                        '`total = 10; total = total / 2; total += 3`. Qual é total?',
                        '8',
                        '5',
                    ),
                ),
            ),
            _ConceptContent(
                'Expressões aritméticas',
                'Combinar operadores e parênteses.',
                'Resolve a expressão respeitando operadores e parênteses.',
                (
                    ('Qual é `2 + 3 * 4`?', '14', '20'),
                    ('Qual é `(2 + 3) * 4`?', '20', '14'),
                    ('Qual é `10 - 6 / 2`?', '7', '2'),
                    ('Qual é `4 * (3 + 2)`?', '20', '14'),
                    ('Qual é `18 / 3 + 2`?', '8', '3'),
                    ('Qual é `9 - (2 + 1)`?', '6', '8'),
                    ('Qual é `3 * 3 + 1`?', '10', '12'),
                    ('Qual é `(12 - 4) / 2`?', '4', '10'),
                    ('Qual é `5 + 2 * (4 - 1)`?', '11', '21'),
                ),
            ),
        ),
        diagnostic_titles=(
            'Diagnóstico: guardar valores',
            'Diagnóstico: atualizar estado',
            'Diagnóstico: calcular expressões',
        ),
        learning_titles=(
            'Primeiras variáveis',
            'Valores em movimento',
            'Contas com parênteses',
            'Planilha de pontos',
            'Orçamento calculado',
            'Desafio de expressões',
        ),
    ),
    _GroupContent(
        competency_index=2,
        concepts=(
            _ConceptContent(
                'Comparações e limites',
                'Comparar valores incluindo fronteiras.',
                'Distingue maior, menor e igualdade no limite.',
                (
                    ('`5 > 0` é verdadeiro?', 'Sim', 'Não'),
                    ('`0 < 0` é verdadeiro?', 'Não', 'Sim'),
                    ('`-2 < 0` é verdadeiro?', 'Sim', 'Não'),
                    ('`18 >= 18` é verdadeiro?', 'Sim', 'Não'),
                    (
                        'A entrada é permitida a partir de 18 anos, incluindo 18. Qual condição expressa a regra?',
                        'idade >= 18',
                        'idade > 18',
                    ),
                    ('`10 <= 9` é verdadeiro?', 'Não', 'Sim'),
                    ('`-1 > -3` é verdadeiro?', 'Sim', 'Não'),
                    (
                        'Um intervalo inclui 10 e 20. O valor 20 deve passar em qual teste do limite superior?',
                        'valor <= 20',
                        'valor < 20',
                    ),
                    (
                        'A promoção vale de 10 a 20, inclusive. O valor 21 está dentro da faixa?',
                        'Não',
                        'Sim',
                    ),
                ),
            ),
            _ConceptContent(
                'Decisão condicional',
                'Escolher o ramo certo entre alternativas.',
                'Executa exatamente o ramo compatível com a condição.',
                (
                    ('Se n > 0 imprime P; senão N. Para n=2, qual saída?', 'P', 'N'),
                    ('Se n < 0 imprime N; senão Z. Para n=0, qual saída?', 'Z', 'N'),
                    (
                        (
                            'Se n > 0 imprime P; senão se n < 0 imprime N; senão Z. '
                            'Para n=-3 e n=0, quais saídas, nessa ordem?'
                        ),
                        'N e Z',
                        'N e P',
                    ),
                    (
                        'Se saldo < 0 imprime dívida; senão ok. Saldo -1?',
                        'dívida',
                        'ok',
                    ),
                    (
                        'Após testar n > 0 e n < 0, qual ramo ainda precisa ser tratado?',
                        'n igual a zero',
                        'n maior que zero',
                    ),
                    (
                        'Se temp > 30 imprime quente; senão ameno. Temp 30?',
                        'ameno',
                        'quente',
                    ),
                    ('Se n > 0 P, senão se n < 0 N, senão Z. n=0?', 'Z', 'P'),
                    (
                        'Se estoque < 0 imprime erro; senão se estoque === 0 imprime repor; senão vender. Estoque 1?',
                        'vender',
                        'repor',
                    ),
                    (
                        'Se x < 0 imprime negativo; senão se x === 0 imprime zero; senão positivo. x=0?',
                        'zero',
                        'positivo',
                    ),
                ),
            ),
        ),
        diagnostic_titles=(
            'Diagnóstico: comparar números',
            'Diagnóstico: escolher o ramo',
            'Diagnóstico: casos limite',
        ),
        learning_titles=(
            'Classificar um número',
            'Porta de entrada',
            'Limite de idade',
            'Faixas de resultado',
            'Sinal e fronteira',
            'Decisões com exceção',
        ),
    ),
    _GroupContent(
        competency_index=2,
        concepts=(
            _ConceptContent(
                'E lógico',
                'Exigir duas condições verdadeiras.',
                'Aplica conjunção inclusive quando só um requisito é atendido.',
                (
                    ('Tem senha e documento. Ambos true. Libera?', 'Sim', 'Não'),
                    ('Tem senha mas não documento. Libera?', 'Não', 'Sim'),
                    ('Não tem senha nem documento. Libera?', 'Não', 'Sim'),
                    (
                        'Pedido exige pagamento e endereço. Ambos prontos. Envia?',
                        'Sim',
                        'Não',
                    ),
                    (
                        'O pedido só sai se pagamento e endereço estiverem prontos. Qual operador une os requisitos?',
                        '&&',
                        '||',
                    ),
                    (
                        'Acesso exige crachá e cadastro. Só cadastro. Libera?',
                        'Não',
                        'Sim',
                    ),
                    ('`true && false` vale?', 'false', 'true'),
                    (
                        'Acesso exige senha, crachá e documento. Falta só o crachá. Libera?',
                        'Não',
                        'Sim',
                    ),
                    (
                        'Acesso exige senha, crachá e documento. Os três estão presentes. Libera?',
                        'Sim',
                        'Não',
                    ),
                ),
            ),
            _ConceptContent(
                'OU lógico',
                'Aceitar uma alternativa válida.',
                'Aplica disjunção quando uma, ambas ou nenhuma alternativa vale.',
                (
                    ('Aceita cartão ou QR. Só QR. Entra?', 'Sim', 'Não'),
                    ('Aceita cartão ou QR. Nenhum. Entra?', 'Não', 'Sim'),
                    ('Aceita cartão ou QR. Ambos. Entra?', 'Sim', 'Não'),
                    ('Basta telefone ou e-mail. Só e-mail. Contata?', 'Sim', 'Não'),
                    (
                        'Basta telefone ou e-mail. Qual operador permite qualquer uma das duas alternativas?',
                        '||',
                        '&&',
                    ),
                    ('Basta telefone ou e-mail. Ambos. Contata?', 'Sim', 'Não'),
                    ('`false || true` vale?', 'true', 'false'),
                    (
                        'Aceita QR, cartão ou convite. Há somente convite. Entra?',
                        'Sim',
                        'Não',
                    ),
                    (
                        'Aceita QR, cartão ou convite. Não há nenhum deles. Entra?',
                        'Não',
                        'Sim',
                    ),
                ),
            ),
            _ConceptContent(
                'NÃO lógico',
                'Inverter uma condição booleana.',
                'Reconhece bloqueio ou ausência por negação sem confundir E/OU.',
                (
                    ('`!true` vale?', 'false', 'true'),
                    ('`!false` vale?', 'true', 'false'),
                    ('Se bloqueado=false, `!bloqueado` vale?', 'true', 'false'),
                    ('Se bloqueado=true, `!bloqueado` vale?', 'false', 'true'),
                    (
                        'Para permitir apenas usuários não bloqueados, qual expressão representa a regra?',
                        '!bloqueado',
                        'bloqueado',
                    ),
                    ('Se ativo=true, `!ativo` vale?', 'false', 'true'),
                    ('Se vazio=true, `!vazio` vale?', 'false', 'true'),
                    (
                        '`bloqueado=true; ativo=!bloqueado; !ativo` vale?',
                        'true',
                        'false',
                    ),
                    (
                        '`cancelado=false; disponivel=!cancelado; !disponivel` vale?',
                        'false',
                        'true',
                    ),
                ),
            ),
        ),
        diagnostic_titles=(
            'Diagnóstico: duas condições',
            'Diagnóstico: alternativas',
            'Diagnóstico: negar estados',
        ),
        learning_titles=(
            'Duas exigências',
            'Alternativas de contato',
            'Bloqueios explícitos',
            'Regras de acesso',
            'Operadores em conjunto',
            'Desafio de condições',
        ),
    ),
    _GroupContent(
        competency_index=3,
        concepts=(
            _ConceptContent(
                'Repetição por quantidade',
                'Contar execuções de um laço.',
                'Conta as iterações de um laço com limite conhecido.',
                (
                    ('`for (i=0; i<3; i++)`. Quantas execuções?', '3', '4'),
                    ('`for (i=1; i<=3; i++)`. Quantas execuções?', '3', '2'),
                    ('`for (i=0; i<0; i++)`. Quantas execuções?', '0', '1'),
                    ('Uma tarefa roda 5 vezes. Quantas saídas produz?', '5', '4'),
                    ('`for (i=2; i<5; i++)`. Quantas execuções?', '3', '5'),
                    ('`for (i=1; i<6; i+=2)`. Quantas execuções?', '3', '2'),
                    ('`for (i=4; i>0; i--)`. Quantas execuções?', '4', '5'),
                    ('`for (i=0; i<=4; i+=2)`. Quantas execuções?', '3', '2'),
                    ('`for (i=10; i<10; i++)`. Quantas execuções?', '0', '1'),
                ),
            ),
            _ConceptContent(
                'Condição de parada',
                'Encerrar quando a condição deixa de valer.',
                'Identifica a atualização necessária e o estado terminal.',
                (
                    ('`n=0; while(n<2){n++}`. Qual valor final?', '2', '1'),
                    ('`n=3; while(n<3){n++}`. Quantas execuções?', '0', '1'),
                    ('`n=5; while(n>2){n--}`. Qual valor final?', '2', '3'),
                    (
                        'Contador começa em 1 e cresce até 4. Quando para?',
                        'Ao chegar a 4',
                        'Ao chegar a 3',
                    ),
                    (
                        '`while(restam > 0)` não termina porque restam nunca muda. Qual correção permite parar?',
                        'Diminuir restam dentro do laço',
                        'Manter restam igual',
                    ),
                    (
                        '`while(x<5)` com x iniciado em 2: qual mudança permite parar?',
                        'Aumentar x',
                        'Manter x',
                    ),
                    ('`n=0; while(n!==3){n++}`. Qual n final?', '3', '2'),
                    ('`n=10; while(n>=8){n--}`. Qual n final?', '7', '8'),
                    ('`while(restam>0)` com restam=0: quantas execuções?', '0', '1'),
                ),
            ),
        ),
        diagnostic_titles=(
            'Diagnóstico: contar passos',
            'Diagnóstico: parar um laço',
            'Diagnóstico: limite de iterações',
        ),
        learning_titles=(
            'Contar três passos',
            'Repetir uma tarefa',
            'Percorrer uma faixa',
            'Sair do ciclo',
            'Contadores e limites',
            'Desafio de repetição',
        ),
    ),
    _GroupContent(
        competency_index=4,
        concepts=(
            _ConceptContent(
                'Dividir em etapas',
                'Separar uma tarefa em operações claras.',
                'Identifica funções com responsabilidades distintas.',
                (
                    (
                        'Para calcular e mostrar um total, qual divisão faz sentido?',
                        'Calcular e depois mostrar',
                        'Misturar entrada e saída',
                    ),
                    (
                        'Para validar e salvar um pedido, o que vem primeiro?',
                        'Validar',
                        'Salvar',
                    ),
                    (
                        'Para ler, transformar e mostrar dados, qual ordem?',
                        'Ler, transformar, mostrar',
                        'Mostrar, ler, transformar',
                    ),
                    (
                        'Uma função `somar` também envia e-mail. Qual ajuste?',
                        'Separar o envio',
                        'Adicionar mais efeitos',
                    ),
                    (
                        'Para gerar recibo, calcule total e depois formate. Qual primeira etapa?',
                        'Calcular total',
                        'Formatar recibo',
                    ),
                    (
                        'Qual função tem responsabilidade mais clara?',
                        'calcularDesconto',
                        'fazerTudo',
                    ),
                    (
                        'Entrada, cálculo e apresentação: quantas etapas nomeadas?',
                        'Três',
                        'Uma',
                    ),
                    (
                        'Para trocar só o cálculo do frete, onde alterar?',
                        'Na função de frete',
                        'Em todas as etapas',
                    ),
                    (
                        'Uma rotina lê dados e calcula imposto. Como facilitar teste?',
                        'Extrair o cálculo',
                        'Adicionar impressão',
                    ),
                ),
            ),
            _ConceptContent(
                'Parâmetros e retorno',
                'Receber argumentos e devolver um resultado.',
                'Relaciona argumentos, parâmetro e valor retornado.',
                (
                    ('`dobrar(3)` retorna `3*2`. Qual resultado?', '6', '3'),
                    ('`somar(2,4)` retorna a+b. Qual resultado?', '6', '2'),
                    ('`triplicar(0)` retorna x*3. Qual resultado?', '0', '3'),
                    (
                        '`descontar(10,2)` retorna preço-desconto. Qual resultado?',
                        '8',
                        '12',
                    ),
                    (
                        '`saudar("Ana")` retorna "Oi, " + nome. Qual resultado?',
                        'Oi, Ana',
                        'Oi, nome',
                    ),
                    (
                        '`maior(5,8)` retorna o maior argumento. Qual resultado?',
                        '8',
                        '5',
                    ),
                    ('`area(3,4)` retorna largura*altura. Qual resultado?', '12', '7'),
                    ('`metade(18)` retorna x/2. Qual resultado?', '9', '18'),
                    ('`somar(0,-2)` retorna a+b. Qual resultado?', '-2', '2'),
                ),
            ),
        ),
        diagnostic_titles=(
            'Diagnóstico: separar etapas',
            'Diagnóstico: passar dados',
            'Diagnóstico: retorno de funções',
        ),
        learning_titles=(
            'Funções pequenas',
            'Entrada e retorno',
            'Organizar o cálculo',
            'Reutilizar etapas',
            'Parâmetros em ação',
            'Desafio de decomposição',
        ),
    ),
)


_CODE_EXAMPLES = {
    0: (
        (
            'Acompanhe a sequência. Complete `calcularTotal` para somar 2 e depois multiplicar por 3. '
            'A saída deve ser 9 para entrada 1 e 12 para entrada 2.'
        ),
        'function calcularTotal(inicial) {\n  // Some 2; depois multiplique por 3.\n  return inicial\n}\nfor (const n of [1, 2]) console.log(calcularTotal(n))\n',
        'A sequência aplica a soma antes da multiplicação e produz 9 e 12.',
    ),
    1: (
        (
            'Complete `novoSaldo` para guardar o saldo inicial, acrescentar o depósito e subtrair o gasto. '
            'As entradas (10, 5, 3) e (0, 7, 2) devem produzir 12 e 5.'
        ),
        'function novoSaldo(saldo, deposito, gasto) {\n  // Atualize o valor em etapas.\n  return saldo\n}\nfor (const dados of [[10, 5, 3], [0, 7, 2]]) console.log(novoSaldo(...dados))\n',
        'A solução usa os três valores na ordem correta e produz 12 e 5.',
    ),
    2: (
        (
            'Complete `classificarNumero`: retorne `positivo` se `numero > 0`, `negativo` se '
            '`numero < 0` e `zero` se `numero === 0`. Considere as três chamadas ao final do arquivo.'
        ),
        'function classificarNumero(numero) {\n  // Escreva sua decisão aqui.\n}\n\nclassificarNumero(5)\nclassificarNumero(-3)\nclassificarNumero(0)\n',
        'Classifica 5 como positivo, -3 como negativo e 0 como zero, com três ramos corretos.',
    ),
    3: (
        (
            'Complete `contarAte` para devolver uma lista de 1 até limite, inclusive. '
            'Para 3, mostre 1,2,3; para 0, mostre uma linha vazia.'
        ),
        'function contarAte(limite) {\n  const numeros = []\n  // Repita apenas enquanto houver números na faixa.\n  return numeros.join(",")\n}\nfor (const n of [3, 0]) console.log(contarAte(n))\n',
        'Produz 1,2,3 para limite 3 e nenhuma entrada para limite 0.',
    ),
    4: (
        (
            'Complete `calcularSubtotal` para devolver preço vezes quantidade e use seu retorno em '
            '`totalComFrete`. Para (4,3,2) e (5,0,2), mostre 14 e 2.'
        ),
        'function calcularSubtotal(preco, quantidade) {\n  // Devolva somente o subtotal.\n  return 0\n}\nfunction totalComFrete(preco, quantidade, frete) {\n  return calcularSubtotal(preco, quantidade) + frete\n}\nfor (const dados of [[4, 3, 2], [5, 0, 2]]) console.log(totalComFrete(...dados))\n',
        'A função de subtotal recebe dois parâmetros, retorna o produto e compõe 14 e 2.',
    ),
}

_CODE_CONCEPT_EVIDENCE = {
    0: (
        'Executa a soma de 2 antes da multiplicação por 3.',
        'Apresenta o resultado calculado para as entradas 1 e 2.',
        'Acompanha o valor intermediário antes de devolver 9 ou 12.',
    ),
    1: (
        'Recebe e usa os três valores de entrada sem trocar seus papéis.',
        'Atualiza o saldo primeiro com o depósito e depois com o gasto.',
        'Calcula saldo + depósito - gasto, inclusive para saldo inicial zero.',
    ),
    2: (
        'Compara numero com zero e distingue > 0, < 0 e a fronteira 0.',
        'Escolhe exatamente o ramo positivo, negativo ou zero para cada entrada.',
    ),
    3: (
        'Executa uma iteração para cada inteiro de 1 até o limite inclusive.',
        'Encerra no limite e não executa para limite zero.',
    ),
    4: (
        'Separa o cálculo do subtotal da composição com frete.',
        'Passa preço e quantidade como parâmetros e retorna o subtotal correto.',
    ),
}

_CLASSIFY_RUBRIC_CRITERIA = (
    (
        'positive_comparison',
        'Comparação com zero',
        (
            'Reconhece o caso positivo com `numero > 0`. Avalie a comparação separadamente '
            'do retorno: imprimir o texto ou deixar de tratar outros casos não elimina '
            'a evidência desta comparação.'
        ),
        'Não há uma comparação correta que identifique números positivos.',
        'A condição `numero > 0` identifica corretamente o caso positivo.',
    ),
    (
        'positive_return',
        'Retorno do caso positivo',
        (
            'Para `numero > 0`, a função deve retornar a string `positivo`. '
            '`console.log` apenas imprime e não substitui `return`.'
        ),
        'O caso positivo não retorna `positivo`; imprimir o texto não atende ao contrato.',
        'O caso positivo retorna `positivo` para quem chamou a função.',
    ),
    (
        'negative_return',
        'Retorno do caso negativo',
        (
            'A função deve retornar `negativo` quando `numero < 0` e não deve '
            'retornar `negativo` quando `numero >= 0`. Verifique ambos os lados '
            'da condição: um `return "negativo"` incondicional não atende ao critério. '
            'Por exemplo, teste -3, 5 e 0.'
        ),
        (
            'O retorno `negativo` não está restrito a números negativos; '
            'um retorno incondicional também falha neste critério.'
        ),
        'A função retorna `negativo` apenas para números menores que zero.',
    ),
    (
        'zero_return',
        'Retorno do caso zero',
        'Para `numero === 0`, a função deve retornar a string `zero`.',
        'O caso zero não retorna `zero`.',
        'O caso zero retorna `zero`.',
    ),
)

_CLASSIFY_CHOICE_CASES = (
    (
        'Qual comparação identifica um número negativo?',
        'numero < 0',
        'numero > 0',
        'numero === 0',
        'numero >= 0',
    ),
    (
        (
            'Qual ramo é executado?\n\n'
            '```javascript\n'
            'const numero = 5;\n'
            'if (numero > 0) {\n  console.log("positivo");\n'
            '} else if (numero < 0) {\n  console.log("negativo");\n'
            '} else {\n  console.log("zero");\n}\n'
            '```'
        ),
        'positivo',
        'negativo',
        'zero',
        'nenhum ramo',
    ),
    (
        'Para numero = 0, qual comparação é verdadeira?',
        'numero === 0',
        'numero > 0',
        'numero < 0',
        'numero !== 0',
    ),
)

_INITIAL_DIAGNOSTIC_ITEMS = (
    (
        'Ordem de execução',
        ActivityDifficulty.EASY,
        'Ordem das instruções',
        (
            (
                'Qual é o valor final de `x`?\n\n'
                '```javascript\nlet x = 2;\nx = x + 1;\n```'
            ),
            '3',
            '2',
            '1',
            '4',
        ),
    ),
    (
        'Entrada e saída',
        ActivityDifficulty.EASY,
        'Entrada e saída',
        (
            (
                'Qual valor aparece na saída?\n\n'
                '```javascript\nconst idade = 20;\nconsole.log(idade + 1);\n```'
            ),
            '21',
            '20',
            '22',
            '1',
        ),
    ),
    (
        'Atribuição',
        ActivityDifficulty.EASY,
        'Guardar um valor',
        (
            ('Qual é o valor final de `x`?\n\n```javascript\nlet x = 5;\nx = 2;\n```'),
            '2',
            '5',
            '7',
            '0',
        ),
    ),
    (
        'Expressões aritméticas',
        ActivityDifficulty.MEDIUM,
        'Calcular uma expressão',
        _MultipleSelectionCase(
            prompt='Quais expressões resultam em 14? Selecione todas.',
            options=(
                ('`2 + 3 * 4`', True),
                ('`2 + 3 + 4`', False),
                ('`2 * (3 + 4)`', True),
                ('`(2 + 3) * 4`', False),
            ),
        ),
    ),
    (
        'Comparações e limites',
        ActivityDifficulty.EASY,
        'Comparar com zero',
        (
            (
                'Qual comparação é verdadeira para o valor de `n`?\n\n'
                '```javascript\nconst n = 0;\n```'
            ),
            '`n === 0`',
            '`n < 0`',
            '`n > 0`',
            '`n !== 0`',
        ),
    ),
    (
        'Decisão condicional',
        ActivityDifficulty.MEDIUM,
        'Escolher o ramo',
        (
            (
                'Para `n = 0`, qual é a saída?\n\n'
                '```javascript\nif (n < 0) {\n  console.log("N");\n} else {\n  console.log("Z");\n}\n```'
            ),
            'Z',
            'N',
            'P',
            'Nenhuma saída',
        ),
    ),
    (
        'Condição de parada',
        ActivityDifficulty.MEDIUM,
        'Parar a repetição',
        _MultipleSelectionCase(
            prompt=(
                'Quais afirmações são verdadeiras? Selecione todas.\n\n'
                '```javascript\nlet n = 0;\nwhile (n < 3) {\n  n++;\n}\n```'
            ),
            options=(
                ('O corpo executa 3 vezes.', True),
                ('Ao final, `n` vale 2.', False),
                ('Ao final, `n` vale 3.', True),
                ('O corpo executa 4 vezes.', False),
            ),
        ),
    ),
    (
        'Parâmetros e retorno',
        ActivityDifficulty.MEDIUM,
        'Retornar um valor',
        (
            (
                'Qual é o valor de `resultado`?\n\n'
                '```javascript\nfunction dobrar(x) {\n  return x * 2;\n}\n'
                'const resultado = dobrar(4);\n```'
            ),
            '8',
            '4',
            '16',
            '6',
        ),
    ),
)

_PREREQUISITE_NAMES: dict[str, tuple[str, ...]] = {
    'Rastreamento de valores': ('Ordem de execução',),
    'Atribuição': ('Ordem de execução',),
    'Atualização de valores': ('Atribuição',),
    'Expressões aritméticas': ('Atribuição',),
    'Comparações e limites': ('Expressões aritméticas',),
    'Decisão condicional': ('Comparações e limites',),
    'E lógico': ('Decisão condicional',),
    'OU lógico': ('Decisão condicional',),
    'NÃO lógico': ('Decisão condicional',),
    'Repetição por quantidade': ('Ordem de execução',),
    'Condição de parada': ('Decisão condicional',),
    'Dividir em etapas': ('Ordem de execução',),
    'Parâmetros e retorno': ('Dividir em etapas', 'Atribuição'),
}


def _choice_question(
    *, key: str, case: tuple[str, ...], concept: Concept, activity_id: str
) -> SingleChoiceQuestion:
    prompt, correct, *distractors = case
    option_texts = (correct, *distractors)
    # Rotate the displayed position to avoid a predictable answer key.
    correct_index = (int(activity_id[-3:]) + int(key[1:])) % len(option_texts)
    option_texts = (
        *option_texts[1 : correct_index + 1],
        correct,
        *option_texts[correct_index + 1 :],
    )
    return SingleChoiceQuestion(
        key=key,
        prompt=prompt,
        options=tuple(
            ChoiceOption(
                key=chr(ord('a') + index),
                text=text,
                is_correct=index == correct_index,
            )
            for index, text in enumerate(option_texts)
        ),
        correct_explanation=f'A resposta corresponde ao estado ou regra observável: {correct}.',
        incorrect_explanation='Refaça os passos, acompanhe o estado e teste os casos limite antes de tentar novamente.',
        concept_criteria=(
            ChoiceConceptCriterion(
                concept_id=concept.id,
                criterion=concept.observation_criteria,
                examples=f'Neste caso, a resposta correta é {correct}.',
                limits='Esta escolha observa somente o conceito citado; não demonstra implementação de código.',
                correct_score=100,
                incorrect_score=0,
            ),
        ),
    )


def _multiple_selection_question(
    *, key: str, case: _MultipleSelectionCase, concept: Concept
) -> MultipleSelectionQuestion:
    correct_options = tuple(text for text, is_correct in case.options if is_correct)
    return MultipleSelectionQuestion(
        key=key,
        prompt=case.prompt,
        options=tuple(
            ChoiceOption(key=chr(ord('a') + index), text=text, is_correct=is_correct)
            for index, (text, is_correct) in enumerate(case.options)
        ),
        correct_explanation='Todas e somente as afirmações verdadeiras foram selecionadas.',
        incorrect_explanation='Verifique cada alternativa antes de selecionar a resposta completa.',
        concept_criteria=(
            ChoiceConceptCriterion(
                concept_id=concept.id,
                criterion=concept.observation_criteria,
                examples=', '.join(correct_options),
                limits='Esta seleção observa somente o conceito citado; não demonstra implementação de código.',
                correct_score=100,
                incorrect_score=0,
            ),
        ),
    )


def _code_question(
    *, activity_id: str, competency_index: int, concepts: tuple[Concept, ...]
) -> tuple[JavascriptStdinQuestion, CodeRubricEvaluationPart]:
    prompt, source, expected = _CODE_EXAMPLES[competency_index]
    concept_evidence = _CODE_CONCEPT_EVIDENCE[competency_index]
    question = JavascriptStdinQuestion(
        key='q4',
        prompt=prompt,
        initial_files=(
            JavascriptInitialFile(path='src/main.js', content=source, editable=True),
        ),
        entrypoint='src/main.js',
        fixed_dependencies=(),
        permitted_commands=(
            JavascriptPermittedCommand(
                id='run-main', executable='node', arguments=('src/main.js',)
            ),
        ),
        concept_criteria=tuple(
            CodeConceptCriterion(
                concept_id=concept.id,
                description=f'Demonstra {concept.name}: {concept_evidence[index]}',
                level_observations=tuple(
                    CodeLevelObservation(
                        id=f'{activity_id}-{concept.id[-3:]}-evidence-{level}',
                        level=level,
                        evidence=(
                            {
                                0: f'Não há evidência observável de {concept.name}.',
                                25: f'Há uma tentativa de {concept.name}, mas os exemplos básicos falham.',
                                50: f'{concept.name} funciona em um exemplo, mas não nos demais.',
                                75: f'{concept.name} funciona nos exemplos comuns; revise um caso limite.',
                                100: concept_evidence[index],
                            }[level]
                        ),
                        interpretation_limit=(
                            'Observe apenas este conceito na resposta. Aceite soluções equivalentes; '
                            'se o mecanismo não for observável, registre inconclusivo. '
                            'A execução de prática não é nota oficial.'
                        ),
                    )
                    for level in (0, 25, 50, 75, 100)
                ),
                inconclusive_observation=CodeInconclusiveObservation(
                    id=f'{activity_id}-{concept.id[-3:]}-evidence-inconclusive',
                    text=f'A resposta pode estar correta, mas não permite observar {concept.name} com segurança.',
                ),
            )
            for index, concept in enumerate(concepts)
        ),
    )
    if activity_id == LOGIC_CLASSIFY_ACTIVITY_ID:
        criteria = tuple(
            CodeRubricCriterion(
                key=key,
                name=name,
                description=description,
                weight_percentage=25,
                required=True,
                fixed_comments=tuple(
                    CodeRubricComment(
                        id=f'{activity_id}-{key}-comment-{level}',
                        level=level,
                        text={
                            0: absent_comment,
                            25: f'Há uma tentativa de {name.lower()}, mas ela ainda falha nos exemplos.',
                            50: f'{name} funciona em parte dos exemplos; revise os demais casos.',
                            75: f'{name} funciona nos casos comuns; revise o caso limite.',
                            100: complete_comment,
                        }[level],
                    )
                    for level in (0, 25, 50, 75, 100)
                ),
                inconclusive_comment=CodeInconclusiveComment(
                    id=f'{activity_id}-{key}-comment-inconclusive',
                    text=f'Não foi possível verificar {name.lower()} com segurança.',
                ),
            )
            for key, name, description, absent_comment, complete_comment in _CLASSIFY_RUBRIC_CRITERIA
        )
        return question, CodeRubricEvaluationPart(
            question_key=question.key,
            weight_percentage=25,
            criteria=criteria,
        )

    correctness_rubric = CodeRubricCriterion(
        key='correctness',
        name='Correção e aderência',
        description=(
            f'A implementação respeita o enunciado e produz o comportamento esperado: {expected} '
            'Soluções equivalentes são aceitas.'
        ),
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CodeRubricComment(
                id=f'{activity_id}-correctness-comment-{level}',
                level=level,
                text={
                    0: 'A implementação não atende ao comportamento solicitado.',
                    25: 'Há uma tentativa, mas os exemplos básicos falham.',
                    50: 'Alguns exemplos funcionam; ainda há saídas incorretas.',
                    75: 'A solução está próxima; revise um caso limite.',
                    100: expected,
                }[level],
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CodeInconclusiveComment(
            id=f'{activity_id}-correctness-comment-inconclusive',
            text='Não foi possível verificar a correção; tente novamente.',
        ),
    )
    return question, CodeRubricEvaluationPart(
        question_key=question.key,
        weight_percentage=25,
        criteria=(correctness_rubric,),
    )


def _activity(
    *,
    activity_id: str,
    competency_id: str,
    group: _GroupContent,
    group_concepts: tuple[Concept, ...],
    index: int,
    add_code: bool,
) -> Activity:
    is_diagnostic = index < 3
    difficulty = (
        ActivityDifficulty.EASY,
        ActivityDifficulty.MEDIUM,
        ActivityDifficulty.HARD,
    )[index if is_diagnostic else (index - 3) // 2]
    title = (
        group.diagnostic_titles[index]
        if is_diagnostic
        else group.learning_titles[index - 3]
    )
    chosen = tuple(
        group_concepts[position % len(group_concepts)] for position in range(3)
    )
    by_id = {
        concept.id: content
        for concept, content in zip(group_concepts, group.concepts, strict=True)
    }
    questions = tuple(
        _choice_question(
            key=f'q{position + 1}',
            case=(
                _CLASSIFY_CHOICE_CASES[position]
                if activity_id == LOGIC_CLASSIFY_ACTIVITY_ID
                else by_id[concept.id].cases[
                    (index + (position // len(group_concepts))) % 9
                ]
            ),
            concept=concept,
            activity_id=activity_id,
        )
        for position, concept in enumerate(chosen)
    )
    parts: tuple[CorrectnessEvaluationPart | CodeRubricEvaluationPart, ...] = tuple(
        CorrectnessEvaluationPart(
            question_key=question.key,
            weight_percentage=25 if add_code else (34 if position == 0 else 33),
        )
        for position, question in enumerate(questions)
    )
    if add_code:
        code_question, code_part = _code_question(
            activity_id=activity_id,
            competency_index=group.competency_index,
            concepts=group_concepts,
        )
        questions = (*questions, code_question)
        parts = (*parts, code_part)
    return Activity(
        id=activity_id,
        competency_id=competency_id,
        activity_type=ActivityType.DIAGNOSTIC
        if is_diagnostic
        else ActivityType.LEARNING,
        difficulty=difficulty,
        title=title,
        objective=f'Aplicar {", ".join(concept.name for concept in group_concepts)} em situações observáveis.',
        questions=questions,
        evaluation_rule=EvaluationRule(parts=parts),
    )


def build_logic_programming_seed() -> LogicProgrammingSeed:
    """Build a complete, reproducible Curriculum snapshot without persistence."""
    skill = Skill(
        id=LOGIC_SKILL_ID,
        name='Lógica de programação',
        description='Fundamentos completos para ler, construir e explicar algoritmos.',
        initial_diagnostic_activity_ids=LOGIC_INITIAL_DIAGNOSTIC_ACTIVITY_IDS,
    )
    competencies = tuple(
        Competency(
            id=_id(310 + index),
            skill_id=skill.id,
            name=name,
            description=description,
            position=index + 1,
        )
        for index, (name, description, _) in enumerate(_COMPETENCIES)
    )
    concepts: list[Concept] = []
    materials: list[Material] = []
    activities: list[Activity] = []
    sequence_items: dict[str, list[MaterialSequenceItem | ActivitySequenceItem]] = {
        competency.id: [] for competency in competencies
    }
    concepts_by_name: dict[str, Concept] = {}
    for group_index, group in enumerate(_GROUPS):
        competency = competencies[group.competency_index]
        group_concepts: list[Concept] = []
        for content in group.concepts:
            concept = Concept(
                id=_id(320 + len(concepts)),
                competency_id=competency.id,
                name=content.name,
                description=content.description,
                position=1
                + sum(item.competency_id == competency.id for item in concepts),
                observation_criteria=content.observation,
                prerequisite_ids=tuple(
                    concepts_by_name[name].id
                    for name in _PREREQUISITE_NAMES.get(content.name, ())
                ),
            )
            concepts.append(concept)
            group_concepts.append(concept)
            concepts_by_name[concept.name] = concept
        material = Material(
            id=_id(340 + len(materials)),
            skill_id=skill.id,
            title=f'Introdução: {competency.name}',
            content=_COMPETENCIES[group.competency_index][2],
            material_type=MaterialType.THEORY,
            concept_ids=tuple(concept.id for concept in group_concepts),
        )
        materials.append(material)
        sequence_items[competency.id].append(
            MaterialSequenceItem(
                position=len(sequence_items[competency.id]) + 1, material_id=material.id
            )
        )
        for index in range(9):
            is_diagnostic = index < 3
            activity_id = _id(350 + group_index * 9 + index)
            if group_index == 2 and index == 3:
                activity_id = LOGIC_CLASSIFY_ACTIVITY_ID
            activity = _activity(
                activity_id=activity_id,
                competency_id=competency.id,
                group=group,
                group_concepts=tuple(group_concepts),
                index=index,
                add_code=index == 3 and group_index in (0, 1, 2, 4, 5),
            )
            activities.append(activity)
            if not is_diagnostic:
                sequence_items[competency.id].append(
                    ActivitySequenceItem(
                        position=len(sequence_items[competency.id]) + 1,
                        activity_id=activity.id,
                    )
                )

    for activity_id, (concept_name, difficulty, title, case) in zip(
        LOGIC_INITIAL_DIAGNOSTIC_ACTIVITY_IDS, _INITIAL_DIAGNOSTIC_ITEMS, strict=True
    ):
        concept = concepts_by_name[concept_name]
        question = (
            _multiple_selection_question(key='q1', case=case, concept=concept)
            if isinstance(case, _MultipleSelectionCase)
            else _choice_question(
                key='q1', case=case, concept=concept, activity_id=activity_id
            )
        )
        activities.append(
            Activity(
                id=activity_id,
                competency_id=concept.competency_id,
                activity_type=ActivityType.DIAGNOSTIC,
                difficulty=difficulty,
                title=title,
                objective=f'Observar {concept.name} no diagnóstico inicial.',
                questions=(question,),
                evaluation_rule=EvaluationRule(
                    parts=(
                        CorrectnessEvaluationPart(
                            question_key='q1', weight_percentage=100
                        ),
                    )
                ),
            )
        )

    return LogicProgrammingSeed(
        skill=skill,
        competencies=competencies,
        concepts=tuple(concepts),
        materials=tuple(materials),
        activities=tuple(activities),
        curriculum_sequences=tuple(
            CurriculumSequence(
                competency_id=competency.id, items=tuple(sequence_items[competency.id])
            )
            for competency in competencies
        ),
    )

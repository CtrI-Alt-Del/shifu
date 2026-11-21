# Relatório Técnico — Armazenamento em Nuvem com AWS

## Entrega final — Cenário C: Amazon DynamoDB

| Campo | Valor |
| --- | --- |
| Projeto | Shifu |
| Disciplina | Computação em Nuvem II — FATEC |
| Curso | Desenvolvimento de Software Multiplataforma (DSM) |
| Task | [SHIFU-128](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-128) |
| Sprint informada | SHIFU Sprint 3 |
| Responsável pela task | `gabrielsoliveira1606` |
| Status | Laboratório aplicado, consultado, medido e removido da conta AWS em 20/11/2026. Evidências reais da execução estão em E03–E11. A síntese factual de reflexão foi aprovada pelo responsável da atividade em 20/11/2026. |

| Identificação | Informação |
| --- | --- |
| Grupo | Ctrl Alt Del |
| Integrantes informados nos relatórios anteriores | Thiago Martins; Gabriel da Silva; Kauan Fonseca; João Pedro Carvalho; João Gabriel |
| Responsável pela coleta | Gabriel da Silva |
| Operação técnica | Codex, execução assistida |
| Conta | `565725315792`, confirmada por STS em 20/11/2026 |
| Perfil | `shifu-lab`; usuário IAM `shifu-storage-lab` |
| Região | `us-east-2` (Ohio) |
| Repositório | [CtrI-Alt-Del/shifu](https://github.com/CtrI-Alt-Del/shifu) |
| Data de execução e coleta AWS | 20/11/2026 — horários AWS em UTC; evidências incluem responsável e perfil |
| Data de remoção AWS | 20/11/2026 — tabela ausente e state sem recursos |

O texto distingue o contrato real do Shifu, os dados fictícios e os resultados
observados nos serviços. O enunciado e o template original não foram localizados no repositório; este
relatório segue a estrutura dos relatórios de S3 e RDS e os requisitos
transcritos na solicitação. O trabalho está rastreado em
[SHIFU-128](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-128).

## 1. Objetivo e estado da execução

O laboratório modela atividade do aprendiz com cinco tipos de evento, consulta
por aprendiz e consulta secundária por tipo e dia. Usa eventos fictícios e fica
isolado do runtime do Shifu. O pacote e os scripts estão em
[packages/iac/dynamodb](../../packages/iac/dynamodb/README.md).

Em 20/11/2026, STS confirmou a conta `565725315792` e o usuário IAM
`shifu-storage-lab`. A primeira pré-verificação foi negada por permissões IAM;
esse histórico está em [E00](armazenamento-dynamodb-evidencias/E00-preflight-aws.txt).
Depois da atualização da política pelo responsável, o `terraform apply`
concluiu com dois recursos. A tabela `shifu-dynamodb-lab-83b2c3605a` e o GSI
`EventTypeDayIndex` foram confirmados como ativos.

A carga inicial gravou vinte itens; as consultas `GetItem`, por aprendiz e por
GSI retornaram resultados. A simulação simbólica fez sessenta gravações e o
CloudWatch confirmou 60 unidades de escrita na tabela e 60 no GSI, igual às
respostas `PutItem`. Cost Explorer foi consultado e os recursos foram removidos
com Terraform. A verificação AWS retornou `ResourceNotFoundException`; o state
local ficou com zero recursos gerenciados. Evidências: E03–E09.

## 2. Amazon DynamoDB

### 2.1 Tabela e chaves

| Elemento | Configuração planejada |
| --- | --- |
| Tabela | Nome exclusivo com prefixo `shifu-dynamodb-lab-`, gerado pelo Terraform |
| Região | `us-east-2` |
| Classe e capacidade | Standard, provisionada: 5 RCU e 5 WCU na tabela; 5 RCU e 5 WCU no índice |
| Criptografia | Criptografia do lado do servidor habilitada, gerenciada pelo DynamoDB |
| Chave de partição | `PK=LEARNER#<learner_id>` agrupa o histórico do aprendiz |
| Chave de ordenação | `SK=<timestamp UTC>#<event_id>` permite a ordem temporal e desempata eventos simultâneos |
| GSI | `EventTypeDayIndex`; `GSI1PK=EVENT#<event_type>#<data UTC>` e `GSI1SK=<timestamp UTC>#<learner_id>#<event_id>` |
| Projeção do GSI | `KEYS_ONLY`, para evitar duplicar todos os atributos em cada item do índice |
| Backup e proteção | PITR e proteção contra exclusão desativados durante o laboratório descartável |

A chave principal responde à pergunta “quais eventos pertencem a este aprendiz,
em que ordem?”. O índice responde à pergunta “quais eventos deste tipo ocorreram
neste dia?”. A chave de partição do GSI pode concentrar escritas em um único
tipo/dia quando o volume crescer; um desenho de produção precisaria avaliar
sharding e distribuição com tráfego medido. A consulta ao GSI tem consistência
eventual; a leitura direta por chave pode solicitar consistência forte.

### 2.2 Itens fictícios e schema

O arquivo `fixtures/events.json` contém vinte itens em quatro aprendizes: login,
aula iniciada, resposta de quiz, mensagem ao Mentor e XP concedido. Atributos
variam entre texto, número, decimal, booleano, e campos opcionais dentro do mapa
`attributes`. Os dados são exemplos acadêmicos, não registros pessoais nem
eventos publicados pelo Shifu.

A tabela abaixo mostra um item de cada tipo da fixture, confirmado na consulta
remota por `learner-001` em E05:

| Evento | `PK` / `SK` armazenadas | `GSI1PK` / `GSI1SK` armazenadas | Exemplo de `attributes` |
| --- | --- | --- | --- |
| `login` | `LEARNER#learner-001` / `2026-11-17T09:00:00Z#evt-001` | `EVENT#login#2026-11-17` / `2026-11-17T09:00:00Z#learner-001#evt-001` | `method=password`, `device=desktop`, `success=true` |
| `lesson_started` | `LEARNER#learner-001` / `2026-11-17T09:05:00Z#evt-002` | `EVENT#lesson_started#2026-11-17` / `2026-11-17T09:05:00Z#learner-001#evt-002` | `course_id=course-cloud-01`, `lesson_id=lesson-01`, `position=1` |
| `quiz_answer` | `LEARNER#learner-001` / `2026-11-17T09:12:00Z#evt-003` | `EVENT#quiz_answer#2026-11-17` / `2026-11-17T09:12:00Z#learner-001#evt-003` | `question_id=question-01`, `correct=true`, `score=1`, `answer=A` |
| `mentor_message` | `LEARNER#learner-001` / `2026-11-17T09:18:00Z#evt-004` | `EVENT#mentor_message#2026-11-17` / `2026-11-17T09:18:00Z#learner-001#evt-004` | `conversation_id=conversation-001`, `characters=48`, `attachment_count=0` |
| `xp_granted` | `LEARNER#learner-001` / `2026-11-17T09:20:00Z#evt-005` | `EVENT#xp_granted#2026-11-17` / `2026-11-17T09:20:00Z#learner-001#evt-005` | `amount=10`, `source=activity`, `reference_id=activity-001` |

| Tipo de evento | Quantidade na fixture |
| --- | ---: |
| `login` | 4 |
| `lesson_started` | 4 |
| `quiz_answer` | 4 |
| `mentor_message` | 4 |
| `xp_granted` | 4 |
| **Total** | **20** |

DynamoDB exige tipo para atributos usados como chaves, enquanto o restante do
item pode variar. Isso simplifica evolução de eventos, mas transfere validação,
compatibilidade e qualidade entre versões para os produtores e consumidores.
PostgreSQL aplica tipos e constraints nas colunas persistidas e suporta
consultas relacionais mais amplas.

### 2.3 Carga simbólica e métrica

`scripts/lab.sh simulate` grava sessenta itens exclusivos, um por segundo, e
registra o intervalo UTC, falhas, duração e capacidade que cada resposta
`PutItem` retornar para tabela e índice. A simulação demonstra uma carga pequena
e reproduzível; não tenta saturar capacidade nem demonstrar limite da AWS.

Após a execução, `scripts/lab.sh metrics` consulta
`ConsumedWriteCapacityUnits` no CloudWatch com estatística `Sum` em períodos de
60 segundos. A tabela e o GSI são consultados separadamente com as dimensões
correspondentes. A média de capacidade consumida por segundo é a soma do minuto
dividida por 60, como recomenda a [documentação de métricas do DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html).
Se o CloudWatch não retornar datapoints, isso será relatado como pendência, não
como consumo zero.

Na execução de 20/11/2026, a simulação escreveu 60 itens entre 19:32:17.491 e
19:34:27.547 UTC, em 130,056 segundos, com 0 falhas e intervalo configurado de
1 segundo. As respostas `PutItem` somaram 60 unidades para a tabela e 60 para
o GSI. O CloudWatch, após a janela de publicação dos dados, retornou `Sum=60`
para cada dimensão; a reconciliação foi aprovada. A média sobre o tempo total
foi aproximadamente 0,46 unidade/s para tabela e índice. É uma simulação
simbólica de baixo volume, não um teste de limite ou desempenho máximo da AWS.
Dados completos em [E06](armazenamento-dynamodb-evidencias/E06-simulacao.json) e
[E07](armazenamento-dynamodb-evidencias/E07-cloudwatch.json).

### 2.4 Consultas executadas por CLI

Consultas executadas em 20/11/2026 pelo perfil `shifu-lab`, com Gabriel da
Silva como integrante responsável:

- `GetItem` lê um evento com `PK` e `SK` conhecidos;
- `Query` em `PK=LEARNER#learner-001` lista o histórico do aprendiz em ordem;
- `Query` em `EventTypeDayIndex` procura, por exemplo,
  `EVENT#xp_granted#2026-11-18`.

`GetItem` encontrou o evento consultado; `Query` por `PK` retornou 8 eventos
do aprendiz `learner-001`; `Query` pelo GSI para `xp_granted` em `2026-11-18`
retornou 2 chaves. Como a projeção do GSI é `KEYS_ONLY`, a consulta secundária
retorna as chaves e não os atributos completos do evento. O script registrou a
saída integral, perfil, região, responsável e horário em
[E05](armazenamento-dynamodb-evidencias/E05-consultas.json).

### 2.5 Aplicação, custo e remoção

O Terraform usou state local ignorado pelo Git. Em 20/11, o plano de destruição
mostrou somente dois recursos do laboratório. `terraform destroy` removeu ambos.
Após a remoção, `terraform.tfstate` tinha serial 6 e zero recursos gerenciados;
`DescribeTable` retornou `ResourceNotFoundException`. O registro está em
[E09](armazenamento-dynamodb-evidencias/E09-destroy-aws.txt).

Cost Explorer foi consultado antes e depois do destroy para 20/11/2026,
diariamente, por serviço. Ambas as respostas estavam marcadas
`Estimated=true` e não continham grupo Amazon DynamoDB. Elas listaram serviços
da conta que não são atribuíveis a este laboratório. A ausência do grupo não
prova custo zero, e o total do serviço não pode ser isolado da conta
compartilhada. O registro prévio está em
[E08](armazenamento-dynamodb-evidencias/E08-custos-pre-destroy.txt); a
resposta pós-destroy está em
[E08](armazenamento-dynamodb-evidencias/E08-custos-pos-destroy.json).

## 3. Comparação com o histórico real de XP do Shifu

O Shifu persiste concessões em `gamification_xp_grants` no PostgreSQL. O modelo
atual contém `id`, `account_id`, `fact_id`, `amount`, `origin`, `occurred_at` e
`granted_at`; todos são obrigatórios. A tabela tem chave primária por `id` e
índice não único por `account_id`. A origem JSON contém a fonte e referências
de domínio. O histórico filtra por conta e ordena por `granted_at DESC, id
DESC`. Uma consulta representativa é:

```sql
SELECT id, account_id, fact_id, amount, origin, occurred_at, granted_at
FROM gamification_xp_grants
WHERE account_id = :account_id
ORDER BY granted_at DESC, id DESC;
```

O relatório de RDS comprovou carga fictícia persistida com doze concessões de
XP e consulta agrupada que totalizou 185, 150 e 140 XP para três contas. Esses
valores são evidência da execução RDS, não resultados desta tabela DynamoDB.
Referências do contrato: [modelo SQLAlchemy](../../apps/server/src/shifu/gamification/database/sqlalchemy/models/xp_grant_model.py),
[migração](../../apps/server/migrations/versions/a2f91c6d8e47_create_gamification_tables.py)
e [consulta de histórico](../../apps/server/src/shifu/gamification/database/sqlalchemy/repositories/xp_grants_repository.py).

A fixture DynamoDB reúne eventos variados, enquanto a tabela PostgreSQL registra
concessões de XP. Para comparar XP, filtram-se somente os itens `xp_granted` e
comparam-se conta/aprendiz, fato, valor e os dois horários. Não se presume que
os esquemas ou os momentos do evento e da concessão sejam equivalentes.

O caso real do Shifu também atualiza perfil, nível e conquistas dentro da mesma
transação PostgreSQL da concessão. A consulta atual e o modelo relacional são
mais adequados a essas relações e efeitos atômicos.

## 4. Comparação final e cenário hipotético de escala

Os laboratórios mostram finalidades e custos diferentes. S3 guarda objetos e
demonstrou versão, objeto público restrito e lifecycle; DynamoDB indexa itens
por padrões de chave e mostrou métricas de escrita (quando coletadas); RDS
executou migrações e consultas SQL sobre dados relacionais.

| Critério | S3 | RDS PostgreSQL | DynamoDB |
| --- | --- | --- | --- |
| Custo observado nos relatórios | Saldo informado caiu de US$ 112 para US$ 111; intervalo impreciso e valor não isolado por serviço. | Cost Explorer informou US$ 0,000000029 em 18/11, agregado e estimado; não representa custo mensal da instância. | Cost Explorer em 20/11 estava estimado e não retornou grupo Amazon DynamoDB; não significa custo zero nem isola cobrança da tabela. |
| Controle de schema | Metadados e formatos ficam sob controle da aplicação; S3 armazena bytes dos objetos. | Tipos, constraints, migrações e joins SQL; custo de manter migrações e capacidade do banco. | Tipo dos atributos de chave e flexibilidade no restante; validação do schema cabe aos produtores/consumidores. |
| Backup | Versionamento observado no laboratório; não equivale sozinho a uma cópia isolada nem foi restauração testada. | Retenção automática zero no RDS do exercício; snapshot manual atingiu `available` e foi removido. Restauração não foi testada. | DynamoDB oferece backup sob demanda e PITR gerenciado com até 35 dias; PITR é opcional e cobrado pelo tamanho da tabela; estava desativado no laboratório e a restauração não foi testada. |
| Melhor adequação | Arquivos, mídia, exportações e arquivo bruto. | Entidades e transações relacionadas, como concessão de XP junto a perfil/nível/conquistas. | Eventos e consultas conhecidas por chave, com escala horizontal e schema de item flexível. |

### Projeção didática para um milhão de cadastros

Hipótese de cálculo, sem representar tráfego medido: 1.000.000 de contas
cadastradas; 100.000 ativas por dia; dez eventos por pessoa ativa/dia; trinta
dias de retenção em estado estável; item da tabela até 1 KiB. Resulta em 30
milhões de eventos mensais, cerca de 30 GB de itens base retidos e
aproximadamente 30 milhões de unidades de escrita da tabela mais 30 milhões
de unidades de escrita do GSI, pois cada gravação também atualiza o índice.
Pelo exemplo oficial de DynamoDB Standard on-demand para US East (N. Virginia),
US$ 0,625 por milhão de gravações e US$ 0,25 por GB-mês, o cálculo bruto é
**US$ 37,50/mês em escritas** e **US$ 7,50/mês para 30 GB de itens base**.
O armazenamento do GSI, leituras, PITR ou backups sob demanda, transferência e
impostos são adicionais. O tamanho real do GSI depende dos atributos projetados;
o cálculo não supõe que ele tenha o mesmo tamanho da tabela. Os preços publicados
incluem uma franquia de 25 GB de armazenamento para DynamoDB Standard; o valor
bruto não desconta franquia, créditos ou outros descontos.

Para comparação didática, 30 GB armazenados no S3 Standard custariam cerca de
US$ 0,69/mês no exemplo de preço do relatório S3. Se cada evento fosse um objeto
separado, 30 milhões de PUTs a US$ 0,005 por mil solicitações levariam o total
aproximado a **US$ 150,69/mês**, antes de leitura e transferência. Agrupar
eventos em arquivos reduz solicitações, mas não oferece consulta por chave como
uma tabela DynamoDB. Essa conta usa os preços e hipóteses registrados no
relatório S3, e não uma cotação de produção.

O milhão de cadastros, por si só, não determina custo nem capacidade de RDS.
Concorrência, transações, consultas, tamanho e retenção precisam ser medidos.
O `db.t4g.micro` e os 20 GB gp3 do laboratório não são estimativa de produção.
O relatório RDS também registrou custo diário estimado e agregado, não preço
mensal de uma instância para um milhão de usuários. A estimativa acima é
ilustrativa, não uma recomendação de dimensionamento. Referências: [preços
DynamoDB](https://aws.amazon.com/dynamodb/pricing/), [backup e recuperação
PITR](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Point-in-time-recovery.html),
[preços S3](https://aws.amazon.com/s3/pricing/) e [AWS Pricing Calculator](https://calculator.aws/).

Para S3, 30 GB em S3 Standard correspondem a cerca de US$ 0,69/mês no preço
publicado de exemplo. Se cada evento for gravado como objeto separado, 30
milhões de PUTs a US$ 0,005 por mil requisições acrescentam cerca de US$ 150,
para **US$ 150,69/mês** antes de leituras e transferência. Agregar eventos em
arquivos muda o número de requisições e o formato da consulta; S3 não oferece o
mesmo acesso indexado de uma tabela DynamoDB. Referências: [preços S3](https://aws.amazon.com/s3/pricing/)
e [exemplo AWS de armazenamento e PUTs S3 Standard](https://aws.amazon.com/blogs/storage/monitor-data-transfer-costs-related-to-amazon-s3-replication/).

O milhão de cadastros, sozinho, não determina capacidade ou custo de RDS. É
necessário medir concorrência, transações, consultas, tamanho e retenção. A
instância de laboratório `db.t4g.micro` com 20 GB gp3 não é estimativa de
capacidade para produção. Para RDS, a comparação usa as configurações e
limitações de custo observadas no relatório SHIFU-127 e recomenda refazer uma
estimativa de dimensionamento por workload no [AWS Pricing Calculator](https://calculator.aws/).

### Recomendação

**Não substituir o PostgreSQL do Shifu por DynamoDB com base nesta atividade.**
O histórico de XP faz parte de uma transação que altera dados relacionados, e o
PostgreSQL já atende à consulta por conta. Para um app com um milhão de contas,
o número de cadastros sozinho não justifica escolher DynamoDB. O serviço pode
ser avaliado para eventos de alto volume com consultas previsíveis por chave,
se medições reais demonstrarem essa necessidade e forem definidos idempotência,
distribuição do GSI, consistência, backup/restauração e orçamento. Esta é uma
recomendação técnica para avaliação, não uma decisão de adoção do produto.

## 5. Reflexão do grupo e conclusão

**Síntese factual aprovada pelo responsável da atividade, Gabriel da Silva, em 20/11/2026.** S3 demonstrou objetos, versionamento
e política de acesso, mas o custo foi estimado pelo saldo de créditos e não
isolado por serviço. RDS demonstrou migrações, consultas relacionais e um
snapshot manual, sem testar restauração; seu custo observado também era
estimado e agregado. DynamoDB armazenou eventos fictícios, respondeu às
consultas previstas e teve as métricas da tabela e do índice reconciliadas com
as gravações. A consulta do Cost Explorer não identificou uma linha de custo
para DynamoDB, e isso não comprova custo zero. Os três laboratórios foram
removidos ao final. A execução mostra que dados pequenos de laboratório não
projetam custo de produção e que backup configurado não substitui restauração
ensaiada. O registro da aprovação está em
[E11](armazenamento-dynamodb-evidencias/E11-aprovacao-reflexao.txt).

| Critério de conclusão | Estado atual |
| --- | --- |
| Fixtures com 15 ou mais itens fictícios e cinco tipos | 20 itens validados localmente; E01 e E10 |
| `terraform fmt -check -recursive` | Aprovado; E10 |
| `terraform validate` | Aprovado, sem erros nem avisos, após usar `key_schema` no GSI; E10 |
| `bash -n` e `py_compile` | Aprovados sem erros; E10 |
| Plano Terraform local | 2 recursos a criar, 0 alterar, 0 destruir; perfil `shifu-lab`; E02. `-refresh=false`, sem aplicar |
| Aplicação na conta do grupo e consultas CLI | Concluídas; tabela real e operações documentadas em E03 e E05 |
| Métrica CloudWatch e reconciliação com `PutItem` | Aprovadas; 60 unidades na tabela e 60 no GSI, E06 e E07 |
| Custos observados para DynamoDB | Cost Explorer estimado, sem linha Amazon DynamoDB; não interpretado como custo zero, E08 |
| `terraform destroy`, state vazio e ausência remota | Concluídos; 2 recursos removidos, 0 no state e `ResourceNotFoundException`, E09 |
| Parsing das evidências JSON e verificação de whitespace | Aprovados; E10 |
| Aprovação da síntese factual pelo responsável da atividade | Aprovada em 20/11/2026; E11 |

## 6. Referências

- Relatório anterior de [S3](armazenamento-s3.md) e evidências em `armazenamento-s3-evidencias/`.
- Relatório anterior de [RDS](armazenamento-rds.md) e evidências em `armazenamento-rds-evidencias/`.
- [Arquitetura do Shifu](../architecture.md), [infraestrutura](../infrastructure.md) e [módulos](../modules.md).
- [Métricas DynamoDB e CloudWatch](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html), [backup e restauração](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Backup-and-Restore.html), [PITR](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Point-in-time-recovery.html) e [preços DynamoDB](https://aws.amazon.com/dynamodb/pricing/).
- Enunciado informado: **Atividade 3 — Relato Armazenamento**, Computação em Nuvem II. Descrição transcrita na solicitação; template original não localizado.
- [README do laboratório DynamoDB](../../packages/iac/dynamodb/README.md) e validação final local E10.

Os comandos e os resultados AWS estão registrados em
`armazenamento-dynamodb-evidencias/`, com data, responsável e região. Nenhum
segredo, state Terraform, plano ou armazenamento de sessão foi incluído nas
evidências versionadas.

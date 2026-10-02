# Relatório Técnico — Armazenamento em Nuvem na AWS

## V1 da Atividade 3 — S3, RDS e DynamoDB

| Identificação | Informação |
| --- | --- |
| Projeto | Shifu |
| Disciplina | Computação em Nuvem II |
| Instituição / curso | FATEC — Análise e Desenvolvimento de Sistemas (DSM) |
| Grupo | Ctrl Alt Del |
| Integrantes registrados no relatório S3 do grupo | Thiago Martins; Gabriel da Silva; Kauan Fonseca; João Pedro Carvalho; João Gabriel |
| Turma | DSM — 6º semestre |
| Data desta versão | 02/10/2026 |
| Região planejada | `us-east-1` |
| Conta AWS | Não confirmada |
| Repositório | [CtrI-Alt-Del/shifu](https://github.com/CtrI-Alt-Del/shifu) |
| Código IaC | `iac` |
| AWS CLI local | 1.46.0 (Windows 11, Python 3.14.6) |
| Terraform local | 1.16.4; providers AWS 6.67.0 e Random 3.9.1 |
| Validação local | `fmt -check` e `validate` passaram; PowerShell e JSON passaram validação sintática |
| Situação | Implementação local validada; implantação e evidências AWS pendentes |

> **Limite das evidências:** este relatório não declara que os recursos foram
> criados. A validação de identidade AWS falhou com `InvalidClientTokenId`.
> Nenhum nome real de bucket/tabela, endpoint, snapshot, ID de versão, resultado
> de query ou screenshot de console foi fabricado. Atualize os campos marcados
> como pendentes depois de executar o laboratório com credenciais válidas.
> `terraform plan` parou sem criar recursos: STS retornou HTTP 403
> `InvalidClientTokenId` ao validar `GetCallerIdentity`.

## 1. Amazon S3

### 1.1 Configuração do bucket

O Terraform declara um bucket com nome `shifu-storage-lab-<sufixo aleatório>`
para evitar colisão com nomes globais do S3. A região escolhida para a atividade
é `us-east-1`, conforme o exemplo do pacote. Ela foi mantida como região única
para simplificar a execução acadêmica e permitir consultar os três cenários no
mesmo local; essa escolha não implica menor preço. Confirme a região selecionada
e os custos vigentes na conta antes do `apply`.

| Item | Configuração / resultado observado |
| --- | --- |
| Região escolhida | `us-east-1` (configuração planejada; confirmar na execução) |
| Nome do bucket | A ser preenchido com `terraform output -raw s3_bucket_name` |
| Versionamento | `Enabled` na configuração Terraform; resultado AWS pendente |
| Criptografia padrão | SSE-S3 (`AES256`) |
| Propriedade dos objetos | `BucketOwnerEnforced`, sem ACLs |
| Estado de criação | Ainda não criado; autenticação AWS rejeitada |

**Procedimento para reproduzir**, a partir de `iac`:

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
# Edite terraform.tfvars e informe o IPv4 público real do grupo em /32.
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan
# Revise o plano e os custos antes de confirmar.
terraform apply
terraform output
```

**Evidência E01:** print do bucket no console com nome e região — pendente.
**Evidência E02:** `terraform fmt -check -recursive` e `terraform validate`
passaram localmente. `terraform plan` não avançou para AWS porque STS retornou
HTTP 403 `InvalidClientTokenId`; a aplicação não foi executada.

### 1.2 Arquivos enviados e permissões

O pacote prepara cinco chaves de objetos com tipos diferentes. O PDF é enviado
duas vezes à mesma chave para demonstrar versionamento; por isso são cinco
chaves de objeto e seis versões de conteúdo após os uploads.

| Arquivo | Tipo | Chave S3 | Acesso esperado | Upload |
| --- | --- | --- | --- | --- |
| `exemplo.txt` | TXT | `academic/storage-activity/public/exemplo.txt` | Público, somente leitura | Pendente |
| `exemplo.svg` | Imagem SVG | `academic/storage-activity/private/exemplo.svg` | Privado | Pendente |
| `documento-v1.pdf` e `documento-v2.pdf` | PDF, duas versões | `academic/storage-activity/private/documento-versoes.pdf` | Privado | Pendente |
| `exemplo.json` | JSON | `academic/storage-activity/private/exemplo.json` | Privado | Pendente |
| `historico.csv` | CSV | `academic/storage-activity/archive/historico.csv` | Privado | Pendente |

O critério é deixar público apenas um TXT fictício e sem dados pessoais, para
demonstrar acesso anônimo. A política autoriza `s3:GetObject` apenas para a
chave desse TXT; não permite listagem, escrita pública nem leitura dos objetos
privados. O bloqueio de ACL pública continua ativo. A exceção depende também do
bloqueio de políticas públicas na conta AWS permitir esse bucket.

Comandos de upload (após criar o bucket):

```powershell
$bucket = terraform output -raw s3_bucket_name
aws s3 cp .\fixtures\public\exemplo.txt "s3://$bucket/academic/storage-activity/public/exemplo.txt" --content-type text/plain
aws s3 cp .\fixtures\private\exemplo.svg "s3://$bucket/academic/storage-activity/private/exemplo.svg" --content-type image/svg+xml
aws s3 cp .\fixtures\private\exemplo.json "s3://$bucket/academic/storage-activity/private/exemplo.json" --content-type application/json
aws s3 cp .\fixtures\private\documento-v1.pdf "s3://$bucket/academic/storage-activity/private/documento-versoes.pdf" --content-type application/pdf
aws s3 cp .\fixtures\private\documento-v2.pdf "s3://$bucket/academic/storage-activity/private/documento-versoes.pdf" --content-type application/pdf
aws s3 cp .\fixtures\archive\historico.csv "s3://$bucket/academic/storage-activity/archive/historico.csv" --content-type text/csv
aws s3api list-objects-v2 --bucket $bucket --query "Contents[*].[Key,Size,StorageClass]" --output table
```

**URL pública esperada:** obter com `terraform output -raw s3_public_demo_url` e
confirmar que carrega no navegador — pendente.
**Acesso anônimo ao arquivo privado:** deve falhar com HTTP 403 — verificar e
registrar depois do upload.
**Evidências E03–E04:** listagem dos objetos e carregamento da URL pública —
pendentes.

### 1.3 Versionamento

O bucket declara versionamento habilitado. Os dois PDFs são enviados para
`academic/storage-activity/private/documento-versoes.pdf`; após a operação, o
comando abaixo deve retornar dois `VersionId` diferentes, timestamps e uma
versão atual.

```powershell
aws s3api list-object-versions --bucket $bucket --prefix academic/storage-activity/private/documento-versoes.pdf --query "Versions[*].[VersionId,LastModified,IsLatest]" --output table
```

| Versão | Version ID | Data/hora AWS | Atual |
| --- | --- | --- | --- |
| PDF v1 | Pendente | Pendente | Não, após enviar v2 |
| PDF v2 | Pendente | Pendente | Sim |

**Evidência E05:** print da aba Versions ou saída CLI com os dois IDs —
pendente.

### 1.4 Lifecycle Rule

A regra Terraform aplica-se ao prefixo `academic/storage-activity/archive/` e
move objetos elegíveis para `STANDARD_IA` depois de 30 dias. Versões não atuais
desse prefixo expiram após 90 dias. O arquivo CSV fictício está nesse prefixo.
Uma regra configurada não significa que a mudança de classe já aconteceu: o
serviço executa a transição de maneira assíncrona, após o prazo.

| Filtro | Ação | Prazo |
| --- | --- | --- |
| Prefixo `academic/storage-activity/archive/` | Transição para `STANDARD_IA` | 30 dias |
| Versões não atuais no mesmo prefixo | Expiração | 90 dias |

**Evidência E06:** print da lifecycle rule no console — pendente.

## 2. Amazon RDS for PostgreSQL

### 2.1 Configuração da instância

| Configuração | Valor declarado |
| --- | --- |
| Engine | PostgreSQL |
| Versão | Selecionada pelo RDS conforme a região; versão exata ainda não consultada |
| Classe | `db.t3.micro` |
| Multi-AZ | Não — laboratório Single-AZ |
| Armazenamento alocado | 20 GiB, `gp3`, criptografado |
| Banco inicial | `storage_lab` |
| Backup automático | Retenção de 1 dia |
| Senha administrativa | Gerenciada pelo RDS no Secrets Manager; não incluída no relatório |
| Status | Não provisionado; pendente de credenciais válidas |

**Evidência E07:** instância `Available` no console, com engine, versão,
classe, disponibilidade e armazenamento — pendente.

### 2.2 Conectividade

O Terraform declara uma VPC própria, sub-redes em pelo menos duas AZs e um
Security Group que permite TCP/5432 somente do endereço público do grupo em
CIDR `/32`. O endpoint RDS é público para esta demonstração, mas as demais
origens continuam bloqueadas. O exemplo
`198.51.100.25/32` é reservado para documentação: deve ser substituído pelo
endereço real em `terraform.tfvars` antes do plano e da aplicação.

Cliente previsto: `psql`, usando TLS (`sslmode=require`) e segredo recuperado
do Secrets Manager apenas na sessão local. Não armazene a senha em captura de
tela, repositório ou histórico de comandos.

```powershell
$endpoint = terraform output -raw rds_address
$database = terraform output -raw rds_database_name
$username = terraform output -raw rds_master_username
$secretArn = terraform output -raw rds_master_user_secret_arn
$region = terraform output -raw aws_region
$secret = aws secretsmanager get-secret-value --secret-id $secretArn --region $region --query SecretString --output text | ConvertFrom-Json
$env:PGPASSWORD = $secret.password
try {
    psql "host=$endpoint port=5432 dbname=$database user=$username sslmode=require"
}
finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}
```

**Resultado da conexão:** pendente, pois ainda não existe endpoint RDS
provisionado e `psql` não está instalado neste ambiente local.
**Evidência E08:** cliente com endpoint e conexão estabelecida, sem exibir
senha — pendente.

### 2.3 Dados e queries

O script [`schema-and-seed.sql`](../../iac/sql/schema-and-seed.sql)
cria `learners` e `learning_events`, com chave primária, chave estrangeira,
`TIMESTAMPTZ`, nota decimal, `JSONB` e índice por aprendiz/data. Ele popula 10
aprendizes e 15 eventos fictícios. A conexão deverá executar o DDL e as três
consultas do arquivo [`queries.sql`](../../iac/sql/queries.sql).

DDL preparado:

```sql
CREATE TABLE IF NOT EXISTS learners (
    learner_id VARCHAR(20) PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL,
    cohort VARCHAR(40) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_events (
    event_id VARCHAR(24) PRIMARY KEY,
    learner_id VARCHAR(20) NOT NULL REFERENCES learners (learner_id),
    event_type VARCHAR(40) NOT NULL,
    resource_id VARCHAR(40) NOT NULL,
    score NUMERIC(5, 2),
    occurred_at TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_learning_events_learner_occurred_at
    ON learning_events (learner_id, occurred_at);
```

Queries e resultados observados:

**1. SELECT com filtro — resultado pendente:**

```sql
SELECT event_id, learner_id, resource_id, score, occurred_at
FROM learning_events
WHERE event_type = 'activity_submitted' AND score >= 80
ORDER BY occurred_at;
```

**2. JOIN com nome e turma — resultado pendente:**

```sql
SELECT l.display_name, l.cohort, e.event_type, e.resource_id, e.score
FROM learners AS l
JOIN learning_events AS e ON e.learner_id = l.learner_id
WHERE e.event_type = 'activity_submitted'
ORDER BY l.display_name, e.occurred_at;
```

**3. GROUP BY por tipo — resultado pendente:**

```sql
SELECT event_type, COUNT(*) AS event_count, ROUND(AVG(score), 2) AS average_score
FROM learning_events
GROUP BY event_type
ORDER BY event_count DESC, event_type;
```

| Query | Resultado retornado pelo RDS |
| --- | --- |
| SELECT com filtro | Pendente de execução |
| JOIN learners/events | Pendente de execução |
| GROUP BY event_type | Pendente de execução |

**Evidência E09:** output das três queries no `psql` — pendente.

### 2.4 Snapshot manual

O snapshot deve ser criado depois de inserir os dados e validar as consultas.
Os comandos criam e aguardam o estado `available`:

```powershell
$instance = terraform output -raw rds_instance_identifier
$snapshot = "$instance-manual-$(Get-Date -Format yyyyMMddHHmm)"
aws rds create-db-snapshot --db-instance-identifier $instance --db-snapshot-identifier $snapshot --region $region
aws rds wait db-snapshot-available --db-snapshot-identifier $snapshot --region $region
aws rds describe-db-snapshots --db-snapshot-identifier $snapshot --region $region --query "DBSnapshots[0].[DBSnapshotIdentifier,Status,SnapshotCreateTime]" --output table
```

| Identificador | Status | Criado em |
| --- | --- | --- |
| Pendente | Pendente | Pendente |

**Evidência E10:** snapshot listado com identificador, status e horário —
pendente. Snapshots manuais ficam fora do Terraform `destroy` e devem ter seu
custo considerado no encerramento.

## 3. Amazon DynamoDB

### 3.1 Modelagem da tabela

A tabela é PAY_PER_REQUEST e representa eventos imutáveis de atividade por
usuário. `user_id` é a Partition Key porque distribui usuários pela tabela;
`event_key` é a Sort Key, formada por timestamp ISO-8601 mais identificador do
evento, para ordenar eventos de um mesmo usuário e permitir intervalo temporal.
O GSI `event-type-occurred-at-index` usa `event_type` como chave de partição e
`occurred_at` como chave de ordenação para localizar eventos por tipo e período
sem fazer scan.

| Elemento | Definição |
| --- | --- |
| Nome da tabela | `shifu-storage-lab-events-<sufixo>`; valor AWS pendente |
| Partition Key | `user_id` (String) |
| Sort Key | `event_key` (String, timestamp + `#` + event ID) |
| GSI | `event-type-occurred-at-index`: `event_type` + `occurred_at` |
| Capacidade | `PAY_PER_REQUEST` |
| Criptografia em repouso | Ativada |

**Evidência E11:** tabela ativa e chaves visíveis no console — pendente.

### 3.2 Dados inseridos

O arquivo [`dynamodb-events.json`](../../iac/fixtures/dynamodb-events.json)
contém 15 eventos para `learner-001` até `learner-010`. Além das chaves, há
atributos opcionais de acordo com o evento: `score`, `device`, `language`,
`duration_seconds`, `question_count`, `attempt`, `channel`, `session_id` e
`resource_id`. Essa variação ilustra os atributos flexíveis do DynamoDB.

| Event ID | Usuário | Tipo | Atributos de exemplo |
| --- | --- | --- | --- |
| event-001 | learner-001 | activity_submitted | score, device |
| event-002 | learner-001 | material_viewed | duration_seconds |
| event-003 | learner-002 | activity_submitted | score, device |
| event-004 | learner-002 | diagnostic_completed | question_count |
| event-005 | learner-003 | activity_submitted | score, language |
| event-006 | learner-003 | material_viewed | duration_seconds |
| event-007 | learner-004 | activity_submitted | score, attempt |
| event-008 | learner-004 | mentor_opened | channel |
| event-009 | learner-005 | activity_submitted | score, language |
| event-010 | learner-006 | diagnostic_completed | question_count |
| event-011 | learner-006 | activity_submitted | score, language |
| event-012 | learner-007 | material_viewed | duration_seconds |
| event-013 | learner-008 | activity_submitted | score, language |
| event-014 | learner-009 | activity_submitted | score, attempt |
| event-015 | learner-010 | diagnostic_completed | question_count, device |

Script de inserção: `iac/scripts/seed-dynamodb.ps1`. A confirmação de
escrita no serviço e o print de Explore items continuam pendentes.

### 3.3 Queries e GSI

Consulta todos os eventos de um usuário pela Partition Key e Sort Key:

```powershell
$table = terraform output -raw dynamodb_table_name
$region = terraform output -raw aws_region
aws dynamodb query --table-name $table --region $region --key-condition-expression "user_id = :user" --expression-attribute-values file://fixtures/dynamodb-query-user-001.json
```

Consulta `activity_submitted` pelo GSI; sem o GSI, essa busca exigiria scan ou
outro índice/modelo de dados:

```powershell
aws dynamodb query --table-name $table --index-name event-type-occurred-at-index --region $region --key-condition-expression "event_type = :type" --expression-attribute-values file://fixtures/dynamodb-query-activity-submitted.json
```

Outputs AWS das duas queries: pendentes.
**Evidência E12:** comando e resultado — pendente.

### 3.4 Operação via CLI

O seed executa `aws dynamodb batch-write-item`; o script da simulação também
usa a API de lotes respeitando o máximo de 25 itens por chamada e repetindo
itens não processados.

Chamada AWS CLI feita pelo seed para cada lote:

```powershell
aws dynamodb batch-write-item --request-items "file://$temporaryFile" --region $Region --output json
```

O script recebe `-Operator`, mostra o nome do integrante e imprime a quantidade
inserida; substitua o nome de exemplo pelo operador real da execução.

```powershell
.\scripts\seed-dynamodb.ps1 -Operator "Nome do integrante"
.\scripts\load-test-dynamodb.ps1 -Operator "Nome do integrante"
```

| Campo | Resultado |
| --- | --- |
| Integrante que executará e identificará o comando | A confirmar pelo grupo antes da coleta |
| Integrante registrado para a operação nesta execução | Nenhum; a identidade AWS não autenticou |
| Carga sintética | Configuração padrão: 1.000 eventos, lotes de 25 |
| Meta acadêmica | 50 eventos por segundo, métrica média de itens gravados |
| Duração e taxa observadas | Pendentes; nenhuma carga enviada à AWS |

Não confundir a meta definida no script com uma medição real nem com uma
garantia para produção.
**Evidência E13:** terminal com nome do membro, comando e saída real —
pendente.

### 3.5 Comparação entre DynamoDB e SQL

Uma representação relacional simplificada da tabela e do índice poderia ser:

```sql
CREATE TABLE user_events (
    user_id       VARCHAR(80) NOT NULL,
    event_key     VARCHAR(120) NOT NULL,
    event_type    VARCHAR(80) NOT NULL,
    occurred_at   TIMESTAMPTZ NOT NULL,
    resource_id   VARCHAR(120),
    session_id    VARCHAR(120),
    attributes    JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (user_id, event_key)
);

CREATE INDEX ix_user_events_type_time
    ON user_events (event_type, occurred_at);
```

No SQL, colunas/tipos e restrições são definidos pelo DDL; registros precisam
respeitar o esquema e relações podem ser garantidas por chaves estrangeiras. O
DynamoDB só exige que atributos usados em chaves tenham o tipo esperado; itens
podem conter atributos opcionais diferentes. Essa flexibilidade reduz migrações
para atributos esparsos, mas transfere consistência de formato para a aplicação.
PostgreSQL oferece joins e consultas ad hoc mais livres. DynamoDB escala para
cargas grandes quando as chaves e consultas são modeladas previamente; GSIs
permitem padrões adicionais de leitura, com armazenamento e escrita adicionais.
Os dois serviços oferecem leituras fortemente consistentes nas condições
definidas pelo produto, mas a leitura de GSI do DynamoDB é eventualmente
consistente. Consistência e custo devem ser escolhidos conforme a consulta, e
não somente a estimativa de número de usuários.

## 4. Análise comparativa

### 4.1 Custo estimado: qual cenário seria mais caro?

Para este laboratório e em funcionamento contínuo, o RDS tende a representar o
maior custo fixo, pois cobra pela instância enquanto ela permanece ligada, além
do armazenamento, backup e possível segredo gerenciado. O S3 é normalmente a
opção de menor custo para poucos arquivos, embora haja cobrança por
armazenamento, requisições, recuperação e transição entre classes. DynamoDB
PAY_PER_REQUEST varia com leituras/escritas e armazenamento; o GSI também
consome capacidade e armazenamento. O custo exato depende da região, tempo de
uso, volume e tarifas da conta e não foi consultado no Pricing Calculator. A
equipe deve estimar antes do `apply`, limitar a duração e registrar custos reais
no Billing Dashboard.

### 4.2 Controle do schema: vantagem ou desvantagem?

O PostgreSQL oferece controle mais explícito do schema: tipos, `NOT NULL`,
chaves primárias e estrangeiras e índices são validados pelo banco. Isso é
vantajoso para dados relacionais e transacionais que exigem integridade, joins
e relatórios; em contrapartida, mudança de estrutura requer migrações e
coordenação dos consumidores. DynamoDB mantém flexibilidade dos atributos e
escala as consultas desenhadas pelas chaves, mas não impõe um schema completo a
cada item nem joins/foreign keys. A flexibilidade ajuda eventos heterogêneos,
mas validações e relações passam a ser responsabilidade da aplicação.

### 4.3 Backup automatizado e gerenciado

Para um banco relacional, RDS fornece o caminho mais direto neste laboratório:
período de retenção de backups automáticos configurado e snapshot manual
disponível na mesma plataforma. DynamoDB também oferece backups gerenciados e
recuperação point-in-time se habilitados, e S3 oferece versionamento/lifecycle,
mas versionamento de objetos não substitui sozinho um plano completo de backup
de banco. A escolha precisa incluir retenção, custo, restauração testada e RPO;
o snapshot manual previsto aqui ainda aguarda a execução real.

### 4.4 Serviço recomendado para um app mobile com 1 milhão de usuários

Para o cenário específico de registrar grande volume de eventos de usuários,
recomenda-se DynamoDB, desde que as consultas principais sejam conhecidas e a
Partition Key distribua a carga sem concentrar escritas. A capacidade sob
demanda simplifica uma demonstração com tráfego variável, mas não transforma
1 milhão de contas em uma garantia de throughput: deve-se modelar hot keys,
limites, GSIs, consistência, tamanho e custo e realizar um teste representativo.
O PostgreSQL continua adequado para relações/transações centrais do produto, e
S3 para arquivos; não é necessário eleger um único banco para todas as
responsabilidades do aplicativo.

## 5. Reflexão do grupo

> Esta reflexão é uma síntese técnica do material e da configuração local, não
> um relato de execução conjunta dos cinco integrantes. Antes da entrega, o
> grupo deve acrescentar experiências reais, dificuldades e divisão de tarefas.

1. A atividade reúne armazenamento de objetos, banco relacional e uma tabela
   NoSQL, que resolvem necessidades distintas.
2. No S3, a chave do objeto organiza o conteúdo, mas a política de acesso é que
   determina quem pode lê-lo.
3. Versionamento preserva o histórico de um objeto, mas as versões também usam
   armazenamento e precisam de retenção.
4. A regra de lifecycle é configurada previamente e só realiza a transição
   depois do prazo, portanto não deve ser descrita como observada imediatamente.
5. O RDS permite relacionar aprendizes e eventos com integridade referencial e
   consultar esse relacionamento por SQL.
6. Restringir PostgreSQL ao IPv4 `/32` demonstra conectividade sem abrir a porta
   do banco para toda a internet.
7. Manter a senha RDS no Secrets Manager evita gravá-la em variáveis versionadas
   ou no relatório.
8. As chaves compostas do DynamoDB atendem consultas por usuário e ordenação
   temporal; um GSI atende a consulta alternativa por tipo do evento.
9. Os atributos opcionais ilustram flexibilidade, enquanto a validação de cada
   evento continua sendo responsabilidade de quem produz o dado.
10. A taxa de uma simulação curta é apenas uma medição daquele tamanho de lote,
    região e ambiente; não é uma previsão de produção.
11. A validação local do Terraform não prova que a conta possui credenciais,
    permissões ou limites para criar os recursos.
12. Na verificação desta preparação, a identidade AWS retornou
    `InvalidClientTokenId`; por isso a infraestrutura não foi implantada nem
    foram inventados resultados para completar as evidências.

| Integrante registrado | Contribuição efetivamente realizada nesta execução | Ação do grupo |
| --- | --- | --- |
| Thiago Martins | Não observada nesta preparação local | Completar com a participação real |
| Gabriel da Silva | Não observada nesta preparação local | Completar com a participação real |
| Kauan Fonseca | Não observada nesta preparação local | Completar com a participação real |
| João Pedro Carvalho | Não observada nesta preparação local | Completar com a participação real |
| João Gabriel | Não observada nesta preparação local | Completar com a participação real |

## Referências

- Enunciado e template: **Atividade 3 — Relato Armazenamento**, Computação em
  Nuvem II.
- [Documentação do Amazon S3](https://docs.aws.amazon.com/pt_br/s3/).
- [Documentação do Amazon RDS for PostgreSQL](https://docs.aws.amazon.com/pt_br/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html).
- [Documentação do Amazon DynamoDB](https://docs.aws.amazon.com/pt_br/amazondynamodb/latest/developerguide/Introduction.html).
- [AWS Pricing Calculator](https://calculator.aws/).
- [Configuração e comandos do laboratório](../../iac/README.md).
- [Arquitetura de infraestrutura do Shifu](../infrastructure.md).

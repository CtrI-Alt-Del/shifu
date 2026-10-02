# Laboratório V1 — armazenamento do Shifu

Este pacote Terraform implementa os três cenários da V1 da Atividade 3:

- **Amazon S3:** cinco chaves de arquivo (SVG, PDF, JSON, CSV e TXT), acesso
  público a um TXT de demonstração, versionamento do PDF e lifecycle para o CSV;
- **Amazon RDS for PostgreSQL:** instância Single-AZ, banco relacional de
  demonstração, acesso limitado ao IPv4 `/32` do grupo e senha gerenciada no
  AWS Secrets Manager;
- **Amazon DynamoDB:** tabela PAY_PER_REQUEST para eventos com Partition Key,
  Sort Key e GSI, 15 registros de exemplo e script de carga simulada.

O laboratório também cria uma VPC pequena com duas sub-redes públicas para que
o endpoint RDS tenha conectividade. Não provisiona EFS, EC2, NAT Gateway nem
serviços da aplicação. Os dados são sintéticos; o laboratório não implementa
upload no Mentor nem persiste estado oficial de aprendizagem do Shifu.

## Pré-requisitos

- Terraform CLI `>= 1.8` e `< 2.0`;
- AWS CLI autenticado por perfil ou credenciais com permissão para criar os
  recursos AWS usados pelo laboratório;
- endereço IPv4 público atual do grupo, no formato `/32`;
- cliente PostgreSQL `psql` para executar o schema, as consultas e validar a
  conexão com o RDS.

Troque sempre o CIDR de exemplo por seu IP real. A senha do PostgreSQL é
gerenciada pelo RDS no Secrets Manager. A política pública do S3 libera apenas
`s3:GetObject` para o TXT de demonstração, e depende de a configuração de
bloqueio de acesso público no nível da conta permitir essa exceção. Não inclua
chaves, senhas, estado ou planos Terraform no Git.

## Configuração e validação

No PowerShell, a partir de `iac`:

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
```

Substitua `allowed_client_ipv4_cidr` pelo IPv4 público atual do grupo com sufixo
`/32`, escolha a região e mantenha o arquivo `terraform.tfvars` local. A região
de exemplo é `us-east-1`; consulte disponibilidade dos tipos de instância e os
preços vigentes na conta antes de prosseguir.

```powershell
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan
```

Revise todas as inclusões e possíveis custos no plano. A instância RDS é o
principal custo recorrente do laboratório; a simulação DynamoDB é cobrada por
requisição e o armazenamento dos snapshots manuais persiste após remover o
banco. A senha administrada pelo RDS é armazenada no Secrets Manager, que pode
ter cobrança própria.

```powershell
terraform apply
terraform output
```

`init`, `validate` e `plan` não criam esses recursos; `apply` cria. O estado é
local e ignorado pelo Git. Preserve-o até `destroy`, pois é necessário para o
Terraform localizar os recursos criados.

## Cenário A — Amazon S3

O roteiro envia exatamente cinco chaves: um SVG privado, um PDF privado (com
duas versões na mesma chave), um JSON privado, um CSV privado no prefixo de
archive e um TXT público. Assim, são cinco tipos/formas de arquivo e seis
versões armazenadas no total.

```powershell
$bucket = terraform output -raw s3_bucket_name

aws s3 cp .\fixtures\private\exemplo.svg "s3://$bucket/academic/storage-activity/private/exemplo.svg" --content-type image/svg+xml
aws s3 cp .\fixtures\private\exemplo.json "s3://$bucket/academic/storage-activity/private/exemplo.json" --content-type application/json

$versionedKey = "s3://$bucket/academic/storage-activity/private/documento-versoes.pdf"
aws s3 cp .\fixtures\private\documento-v1.pdf $versionedKey --content-type application/pdf
aws s3 cp .\fixtures\private\documento-v2.pdf $versionedKey --content-type application/pdf
aws s3api list-object-versions --bucket $bucket --prefix academic/storage-activity/private/documento-versoes.pdf --query "Versions[*].[VersionId,LastModified,IsLatest]" --output table

aws s3 cp .\fixtures\archive\historico.csv "s3://$bucket/academic/storage-activity/archive/historico.csv" --content-type text/csv
aws s3 cp .\fixtures\public\exemplo.txt "s3://$bucket/academic/storage-activity/public/exemplo.txt" --content-type text/plain
terraform output -raw s3_public_demo_url
```

Abra a URL pública no navegador. Use `aws s3api list-objects-v2 --bucket $bucket`
para confirmar as cinco chaves. O bloqueio de ACLs públicas permanece ligado;
somente a política de leitura da chave pública nomeada é permitida. O CSV no
prefixo `academic/storage-activity/archive/` muda para `STANDARD_IA` depois de
30 dias, conforme a regra, e versões não atuais desse prefixo expiram depois de
90 dias. Lifecycle é assíncrono: a transição não ocorre durante o teste
imediato.

## Cenário B — Amazon RDS for PostgreSQL

O banco usa uma instância `db.t3.micro` Single-AZ, 20 GiB `gp3` criptografados,
retenção de backup automático de um dia e PostgreSQL. O RDS seleciona a versão
disponível na região e ela deve ser registrada pelo output `rds_engine_version`.
O endpoint é público para permitir a conexão acadêmica, mas o Security Group
aceita TCP/5432 somente do CIDR `/32` do grupo. Não abra a porta para
`0.0.0.0/0`.

```powershell
$endpoint = terraform output -raw rds_address
$database = terraform output -raw rds_database_name
$username = terraform output -raw rds_master_username
$secretArn = terraform output -raw rds_master_user_secret_arn
$region = terraform output -raw aws_region
$secret = aws secretsmanager get-secret-value --secret-id $secretArn --region $region --query SecretString --output text | ConvertFrom-Json
$env:PGPASSWORD = $secret.password
try {
    psql "host=$endpoint port=5432 dbname=$database user=$username sslmode=require" -v ON_ERROR_STOP=1 -f .\sql\schema-and-seed.sql
    psql "host=$endpoint port=5432 dbname=$database user=$username sslmode=require" -v ON_ERROR_STOP=1 -f .\sql\queries.sql
}
finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}
```

O SQL cria 10 aprendizes e 15 eventos sintéticos, com FK, tipos, timestamps,
JSONB e índice. `queries.sql` executa filtro, `JOIN` e agregação `GROUP BY`;
salve os três outputs reais para o relatório. Não imprima nem inclua o conteúdo
do segredo nas evidências.

Crie e aguarde o snapshot manual depois de executar as consultas:

```powershell
$instance = terraform output -raw rds_instance_identifier
$snapshot = "$instance-manual-$(Get-Date -Format yyyyMMddHHmm)"
aws rds create-db-snapshot --db-instance-identifier $instance --db-snapshot-identifier $snapshot --region $region
aws rds wait db-snapshot-available --db-snapshot-identifier $snapshot --region $region
aws rds describe-db-snapshots --db-snapshot-identifier $snapshot --region $region --query "DBSnapshots[0].[DBSnapshotIdentifier,Status,SnapshotCreateTime]" --output table
```

O snapshot manual não é gerenciado pelo estado Terraform e não é excluído por
`destroy`; ele pode continuar gerando custo. Remova-o somente depois de salvar
as evidências e se o grupo não precisar preservá-lo.

## Cenário C — Amazon DynamoDB

`user_id` é a Partition Key e `event_key` é a Sort Key, formada por timestamp
ISO-8601 e identificador do evento. A chave distribui eventos entre usuários e
ordena seus registros no mesmo usuário. O GSI
`event-type-occurred-at-index` usa `event_type` como partition e `occurred_at`
como sort, permitindo consultas por tipo/data sem scan. A tabela usa
`PAY_PER_REQUEST` e criptografia em repouso.

Insira os 15 itens sintéticos e consulte todos os eventos de um usuário:

```powershell
.\scripts\seed-dynamodb.ps1 -Operator "Nome do integrante"
$table = terraform output -raw dynamodb_table_name
$region = terraform output -raw aws_region
aws dynamodb query --table-name $table --region $region --key-condition-expression "user_id = :user" --expression-attribute-values file://fixtures/dynamodb-query-user-001.json
```

Consulte eventos por tipo pelo índice GSI:

```powershell
aws dynamodb query --table-name $table --index-name event-type-occurred-at-index --region $region --key-condition-expression "event_type = :type" --expression-attribute-values file://fixtures/dynamodb-query-activity-submitted.json
```

Execute a simulação de escritas:

```powershell
.\scripts\load-test-dynamodb.ps1 -Operator "Nome do integrante"
```

O script grava 1.000 itens em lotes de até 25, distribuídos entre 100 chaves de
usuário e quatro tipos. A métrica é a média de itens por segundo; a meta
acadêmica é 50 eventos/s. Registre contagem, região, duração e taxa observadas.
O resultado é uma amostra sintética deste ambiente, não uma garantia de
capacidade para um milhão de usuários em produção.

Para representar a tabela em SQL e comparar modelo, joins, escalabilidade e
consistência, consulte a seção 3.5 do relatório
[`armazenamento-v1.md`](../../documentation/reports/armazenamento-v1.md).

## Evidências e relatório

Use o template da atividade e complete o relatório
 [`armazenamento-v1.md`](../documentation/reports/armazenamento-v1.md):
prints da configuração do bucket e dos objetos, URL pública, versões, regra de
lifecycle, RDS Available, conexão e queries, snapshot, tabela e GSI do DynamoDB,
queries/CLI/carga, comparação, reflexão de ao menos dez linhas, integrantes,
identificação do operador da CLI e resultados reais. Não registre segredos.
Para regenerar o DOCX após editar o Markdown (requer `python-docx`):

```powershell
py documentation\reports\build_docx.py
```

## Encerramento

Depois de coletar os artefatos e confirmar que o snapshot será mantido ou
removido:

```powershell
terraform destroy
```

`force_destroy = true` apaga as cinco chaves do bucket e todas as versões.
`destroy` remove também RDS, DynamoDB e a rede criada. Snapshots manuais do RDS
ficam fora do estado Terraform; confira os recursos restantes e o Billing
Dashboard após o encerramento. Não use esta política pública nem estas regras
de remoção para anexos reais do Mentor.

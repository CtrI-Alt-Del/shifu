# Laboratório RDS do Shifu

Esta raiz Terraform provisiona uma instância acadêmica separada do staging. A
instância usa PostgreSQL 17, `db.t4g.micro`, Single-AZ, 20 GB gp3 criptografados
e o banco `shifu`. A rede padrão da conta é consultada, mas não é criada nem
alterada. O Security Group aceita PostgreSQL somente do IPv4 `/32` informado.

## Pré-requisitos

- Terraform >= 1.11 e < 2.0 e AWS CLI autenticado pelo perfil `shifu-lab`;
- permissões AWS para descrever identidade, VPC, sub-redes e rotas, criar e
  excluir os recursos RDS e EC2 desta raiz e consultar custos;
- IPv4 público do integrante que fará a conexão, psql e a extensão VS Code
  Database Client;
- uv e as dependências existentes em `apps/server` para Alembic.

O operador deve conferir que a conta retornada por STS é `565725315792`. No
início da execução de 18/11/2026, o perfil `shifu-lab` estava sem algumas
permissões de leitura e criação. A política foi atualizada durante o laboratório
e as permissões listadas abaixo foram usadas para aplicar os recursos e
executar a limpeza. Para reproduzir uma nova execução, o administrador deve
conceder as ações necessárias para criar, ler,
autorizar a regra de entrada e excluir o grupo de segurança do laboratório
(`ec2:CreateSecurityGroup`, `ec2:DescribeSecurityGroups`,
`ec2:DescribeSecurityGroupRules`, `ec2:DescribeNetworkInterfaces`,
`ec2:AuthorizeSecurityGroupIngress`, `ec2:RevokeSecurityGroupIngress`,
`ec2:RevokeSecurityGroupEgress`,
`ec2:CreateTags` e `ec2:DeleteSecurityGroup`). Também são necessárias as ações
de criação, leitura, etiquetagem e exclusão do grupo de sub-redes, instância e
snapshot do laboratório (`rds:CreateDBSubnetGroup`, `rds:DescribeDBSubnetGroups`,
`rds:DeleteDBSubnetGroup`, `rds:CreateDBInstance`, `rds:DescribeDBInstances`,
`rds:DeleteDBInstance`, `rds:AddTagsToResource`, `rds:CreateDBSnapshot`,
`rds:DescribeDBSnapshots`, `rds:ListTagsForResource` e
`rds:DeleteDBSnapshot`), além das consultas de descoberta descritas neste
roteiro e `ce:GetCostAndUsage`. Restrinja as ações
de escrita à região, VPC e prefixo de recursos do laboratório sempre que o
serviço permitir. Não use o perfil de staging.
Confira os recursos e condições permitidos por cada ação nas referências da
[EC2](https://docs.aws.amazon.com/service-authorization/latest/reference/list_ec2.html),
[RDS](https://docs.aws.amazon.com/service-authorization/latest/reference/list_rds.html)
e [Cost Explorer](https://docs.aws.amazon.com/service-authorization/latest/reference/list_ce.html).

Na primeira validação de 19/11/2026, o dry-run de `CreateSecurityGroup` foi
negado. A declaração dessa ação não deve combinar o ARN do security group e o
ARN da VPC com condições `aws:RequestTag/*` e `aws:TagKeys`: as chaves aceitas
diferem por tipo de recurso. Separe a permissão em uma declaração para
`arn:aws:ec2:us-east-2:565725315792:security-group/*`, com as condições de tags
do laboratório, e outra para
`arn:aws:ec2:us-east-2:565725315792:vpc/vpc-0420e74cba45bc0a9`, apenas com a
condição de região. O dry-run seguinte retornou `DryRunOperation` e não criou
recursos.

O apply criou o identificador aleatório, o subnet group e o security group,
mas falhou porque o provider precisou remover a regra de saída padrão e faltou
`ec2:RevokeSecurityGroupEgress`. O primeiro `terraform destroy` removeu o
identificador e o subnet group, mas faltou `ec2:DescribeNetworkInterfaces` para
concluir a exclusão do SG. A chamada `DeleteSecurityGroup` foi permitida e a
remoção direta foi confirmada; uma nova execução de `terraform destroy`
reconciliou o state vazio.

Para reproduzir o apply, mantenha a declaração de `RevokeSecurityGroupEgress`
limitada ao ARN e às tags do SG do laboratório. Acrescente
`DescribeNetworkInterfaces` à leitura de rede com `Resource: "*"` e escopo da
região. O provider usa a primeira ação para remover a saída padrão declarada
fora do HCL e a segunda para conferir interfaces antes de excluir o SG.
Consulte a tabela de [ações, recursos e chaves de condição EC2](https://docs.aws.amazon.com/service-authorization/latest/reference/list_ec2.html).
Repita o preflight e aplique somente após rever um plano novo. Ao encerrar,
confirme que `terraform destroy` termina sem ações manuais.

Na retomada de 19/11/2026, a instância foi criada, mas a senha temporária
original não ficou disponível para as conexões. Depois que o administrador
atualizou a política IAM, a rotação de senha in-place com
`rds:ModifyDBInstance` foi aplicada com sucesso. O plano teve somente uma
atualização in-place, sem criações ou exclusões. A configuração e o state
convergiram em `password_wo_version=5`. Durante esta execução, a senha
rotacionada ficou somente em arquivo local cifrado por DPAPI dentro de
`.terraform`, ignorado pelo Git. O arquivo foi removido no encerramento,
conforme E11. Em execuções futuras, siga o procedimento abaixo e mantenha a
senha somente em memória.

A declaração IAM necessária para a rotação foi:

```json
{
  "Sid": "ModifyCurrentShifuRdsLabPassword",
  "Effect": "Allow",
  "Action": "rds:ModifyDBInstance",
  "Resource": "arn:aws:rds:us-east-2:565725315792:db:shifu-rds-lab-31b997a3f6"
}
```

As versões write-only 3 e 4 foram registradas no state após tentativas negadas.
A tentativa com versão 5 foi autorizada e aplicada depois da política atualizada.
Não é necessário repetir a rotação para esta execução.

## Pré-verificação da conta e da rede

Execute em PowerShell na raiz do repositório. A pré-verificação para com erro se
a identidade não for a conta do grupo, se a VPC padrão não oferecer DNS, se não
houver sub-redes padrão em pelo menos duas zonas, ou se alguma das sub-redes
selecionadas não tiver rota ativa para um Internet Gateway. Essas condições são
necessárias para a instância pública com acesso restrito pelo `/32`.

```powershell
$profile = 'shifu-lab'
$region = 'us-east-2'
$identity = aws sts get-caller-identity --profile $profile --region $region --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $identity.Account -ne '565725315792') { throw 'Perfil ou conta AWS incorretos.' }

$vpcId = aws ec2 describe-vpcs --profile $profile --region $region --filters Name=is-default,Values=true --query 'Vpcs[0].VpcId' --output text
if ($LASTEXITCODE -ne 0 -or $vpcId -eq 'None') { throw 'VPC padrão indisponível.' }
$vpc = aws ec2 describe-vpcs --profile $profile --region $region --vpc-ids $vpcId --output json | ConvertFrom-Json
if (-not $vpc.Vpcs[0].IsDefault -or -not $vpc.Vpcs[0].EnableDnsSupport -or -not $vpc.Vpcs[0].EnableDnsHostnames) { throw 'A VPC padrão não atende aos requisitos de DNS.' }

$subnets = aws ec2 describe-subnets --profile $profile --region $region --filters "Name=vpc-id,Values=$vpcId" Name=default-for-az,Values=true --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or @($subnets.Subnets | Select-Object -ExpandProperty AvailabilityZone -Unique).Count -lt 2) { throw 'São necessárias sub-redes padrão em pelo menos duas zonas.' }
$routeTables = aws ec2 describe-route-tables --profile $profile --region $region --filters "Name=vpc-id,Values=$vpcId" --output json | ConvertFrom-Json
foreach ($subnet in $subnets.Subnets) {
  $routeTable = $routeTables.RouteTables | Where-Object { @($_.Associations | Where-Object { $_.SubnetId -eq $subnet.SubnetId -or ($_.Main -and -not $_.SubnetId) }).Count -gt 0 } | Select-Object -First 1
  $hasInternetRoute = $routeTable.Routes | Where-Object { $_.DestinationCidrBlock -eq '0.0.0.0/0' -and $_.GatewayId -like 'igw-*' -and $_.State -eq 'active' }
  if (-not $hasInternetRoute) { throw "A sub-rede $($subnet.SubnetId) não tem rota ativa ao Internet Gateway." }
}

$versions = aws rds describe-orderable-db-instance-options --profile $profile --region $region --engine postgres --db-instance-class db.t4g.micro --query "OrderableDBInstanceOptions[?starts_with(EngineVersion, '17.')].EngineVersion" --output text
if ($LASTEXITCODE -ne 0 -or -not $versions) { throw 'PostgreSQL 17 db.t4g.micro não aparece como opção nesta conta e região.' }

$publicIp = (Invoke-RestMethod -Uri 'https://checkip.amazonaws.com').Trim()
"Conta: $($identity.Account); VPC: $vpcId; sub-redes: $($subnets.Subnets.Count); IP do operador: $publicIp/32"
```

Configure o IPv4 mostrado como `allowed_cidr` em `terraform.tfvars`. Confirme
que é o endereço público da conexão atual do integrante. Nunca use `0.0.0.0/0`.
Confirme também o preço no AWS Pricing Calculator ou Cost Explorer antes de
criar os recursos.

## Formatação, testes e plano

O lockfile desta raiz é próprio. Inicialize providers sem backend remoto e
execute todas as verificações antes do plano:

```powershell
terraform -chdir=packages/iac/rds init -backend=false -input=false -no-color
terraform -chdir=packages/iac/rds fmt -check -recursive -no-color
terraform -chdir=packages/iac/rds validate -no-color
terraform -chdir=packages/iac/rds test -no-color
```

Crie `packages/iac/rds/terraform.tfvars` localmente a partir do exemplo. O
arquivo contém o IP `/32` e é ignorado pelo Git. O identificador RDS recebe um
sufixo aleatório para cada execução. O plano deve mostrar somente recursos desta
raiz; interrompa se apontar para staging ou qualquer recurso preexistente.

A senha mestre é temporária, alfanumérica e fornecida em memória. Terraform a
envia pelo argumento write-only da AWS, sem persistir seu valor em plano ou
estado. Mantenha o mesmo terminal PowerShell aberto até concluir consultas e
migrações:

```powershell
$chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
$env:AWS_PROFILE = 'shifu-lab'
$env:TF_VAR_db_master_password = -join (1..32 | ForEach-Object { $chars[[System.Security.Cryptography.RandomNumberGenerator]::GetInt32($chars.Length)] })
terraform -chdir=packages/iac/rds plan -input=false -lock=false -out .terraform/rds-lab.tfplan -no-color
if ($LASTEXITCODE -ne 0) { throw 'O plano Terraform falhou.' }
terraform -chdir=packages/iac/rds show -no-color .terraform/rds-lab.tfplan
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível revisar o plano.' }
# Aplique somente depois de revisar o plano acima.
terraform -chdir=packages/iac/rds apply -input=false .terraform/rds-lab.tfplan
if ($LASTEXITCODE -ne 0) { throw 'O apply Terraform falhou.' }
$env:PGPASSWORD = $env:TF_VAR_db_master_password
```

Mantenha esse mesmo terminal aberto até terminar as conexões, as migrações, as
consultas e a remoção do banco. Se o apply falhar antes de atualizar a senha,
pare e não tente conectar. Ao encerrar toda a coleta, remova as variáveis temporárias com
`Remove-Item Env:\TF_VAR_db_master_password,Env:\PGPASSWORD,Env:\AWS_PROFILE`.
Não grave a senha em arquivo, histórico, captura ou relatório. Não use
`terraform output -json` para procurar credenciais.

## Migrações e consultas

Confirme o endpoint sem exibir variáveis de ambiente:

```powershell
$dbId = terraform -chdir=packages/iac/rds output -raw db_instance_identifier
$endpoint = terraform -chdir=packages/iac/rds output -raw db_endpoint
$port = terraform -chdir=packages/iac/rds output -raw db_port
aws rds describe-db-instances --profile shifu-lab --region us-east-2 --db-instance-identifier $dbId --query 'DBInstances[0].{Status:DBInstanceStatus,Public:PubliclyAccessible,Version:EngineVersion,Class:DBInstanceClass,MultiAZ:MultiAZ}' --output table
psql "host=$endpoint port=$port dbname=shifu user=shifu_admin sslmode=require" -c 'SELECT current_database(), current_user, version();'
```

Use conexão TLS (`sslmode=require`) tanto no psql quanto na extensão VS Code.
No Database Client, informe host, porta, banco e usuário mostrados acima e a
senha mantida em memória. Capture o endpoint e o estado conectado sem mostrar
senhas, certificados ou tokens.

Gere uma senha aleatória para a role técnica e disponibilize-a em uma variável de
ambiente separada. No prompt interativo do psql, copie-a para a variável psql e
carregue o script versionado:

```powershell
$runtimeChars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
$env:SHIFU_AGENTOS_PASSWORD = -join (1..32 | ForEach-Object { $runtimeChars[[System.Security.Cryptography.RandomNumberGenerator]::GetInt32($runtimeChars.Length)] })
psql "host=$endpoint port=$port dbname=shifu user=shifu_admin sslmode=require" -v database_name=shifu
```

```text
\getenv runtime_password SHIFU_AGENTOS_PASSWORD
\i apps/server/scripts/create_agentos_runtime_role.sql
\unset runtime_password
\q
```

No RDS gerenciado, o SQL da aplicação pode falhar ao tentar alterar
`SUPERUSER`/`NOSUPERUSER`: a role mestra do serviço não tem o atributo
`SUPERUSER`. Isso ocorreu nesta execução e a transação foi revertida. Se
acontecer, registre o erro e não altere nem marque migrações. A role foi então
criada com os atributos padrão seguros do PostgreSQL, sem tentar mudar esses
atributos protegidos; só `LOGIN`, senha e `CONNECT` foram definidos. O DDL
equivalente é:

```sql
SELECT format(
    'CREATE ROLE shifu_agentos_runtime LOGIN PASSWORD %L',
    :'runtime_password'
)
WHERE NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'shifu_agentos_runtime'
)
\gexec

ALTER ROLE shifu_agentos_runtime LOGIN PASSWORD :'runtime_password';
GRANT CONNECT ON DATABASE shifu TO shifu_agentos_runtime;
```

O DDL acima foi enviado pelo cliente psycopg nesta execução. A ausência de
`SUPERUSER`, `CREATEDB` e `CREATEROLE` nas opções mantém os atributos padrão do
papel sem pedir privilégios que o RDS não pode conceder.

A role de runtime usa uma senha diferente da mestre. Limpe
`SHIFU_AGENTOS_PASSWORD` depois da operação:

```powershell
Remove-Item Env:\SHIFU_AGENTOS_PASSWORD -ErrorAction SilentlyContinue
```

O destino Alembic é exclusivamente o novo RDS. Rode o comando a partir de
`apps/server`, sem `--env-file`, sem `poe db:upgrade` e sem seed:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://shifu_admin:$env:PGPASSWORD@$endpoint`:$port/shifu?sslmode=require"
Push-Location apps/server
uv run alembic heads
uv run alembic upgrade head
uv run alembic current
Pop-Location
Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
```

Confirme no RDS que pgvector está disponível antes do upgrade. A role
`shifu_agentos_runtime` deve existir antes da revisão que concede privilégios
a ela. Registre o head e a revisão atual. Não use `alembic stamp` para contornar
falhas. Se houver erro, preserve mensagem e revisão. Depois de tentar corrigir
as dependências, use o schema parcial `rds_lab` somente se a cadeia real
continuar falhando.

Com o head aplicado, use `schema_name=public`. No fallback, crie o schema pelas
definições derivadas das migrações e use `schema_name=rds_lab`:

```powershell
psql "host=$endpoint port=$port dbname=shifu user=shifu_admin sslmode=require" -v ON_ERROR_STOP=1 -v schema_name=public -f packages/iac/rds/fixtures/fictitious-data.sql
psql "host=$endpoint port=$port dbname=shifu user=shifu_admin sslmode=require" -v ON_ERROR_STOP=1 -v schema_name=public -f packages/iac/rds/fixtures/queries.sql
```

Para o fallback, substitua `public` por `rds_lab` nos dois comandos e execute
primeiro o DDL derivado das migrações:

```powershell
psql "host=$endpoint port=$port dbname=shifu user=shifu_admin sslmode=require" -v ON_ERROR_STOP=1 -f packages/iac/rds/fixtures/fallback-schema.sql
```

O SQL carrega três contas pendentes fictícias, cinco metas e doze registros de XP. Os e-mails usam o domínio
reservado `.invalid`, o hash é propositalmente inválido e nenhuma sessão ou
token é criada. Confira as contagens e rode consultas em uma nova conexão para
comprovar persistência. Registre a saída completa sanitizada.

## Snapshot manual, custos e encerramento

Depois das migrações e consultas, crie um snapshot manual com nome derivado do
identificador da instância. Registre identificador, horário UTC e estado
`available`:

```powershell
$snapshotId = "$dbId-manual"
aws rds create-db-snapshot --profile shifu-lab --region us-east-2 --db-instance-identifier $dbId --db-snapshot-identifier $snapshotId --output json
aws rds wait db-snapshot-available --profile shifu-lab --region us-east-2 --db-snapshot-identifier $snapshotId
aws rds describe-db-snapshots --profile shifu-lab --region us-east-2 --db-snapshot-identifier $snapshotId --query 'DBSnapshots[0].{Id:DBSnapshotIdentifier,Status:Status,CreatedAt:SnapshotCreateTime,SizeGB:AllocatedStorage}' --output table
```

Para comparar o uso diário do serviço antes e depois, use o mesmo filtro de
serviço e granularidade, primeiro no período anterior e depois em uma data já
atualizada após a destruição:

```powershell
$dayStart = 'AAAA-MM-DD'
$dayEnd = 'AAAA-MM-DD' # dia seguinte ao início; Cost Explorer usa limite final exclusivo
$filter = '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Relational Database Service"]}}'
aws ce get-cost-and-usage --profile shifu-lab --region us-east-1 --time-period "Start=$dayStart,End=$dayEnd" --granularity DAILY --metrics UnblendedCost --filter $filter --group-by Type=DIMENSION,Key=USAGE_TYPE --output json
```

Registre a resposta ou a negação de acesso. A comparação do serviço inclui
outros bancos da mesma conta, como staging, a menos que os dados de custo
permitam isolar a instância pelo identificador ou pela tag `Environment`. A
AWS pode atualizar os dados em períodos de pelo menos 24 horas. Fonte:
[referência do AWS CLI para os waiters do RDS](https://docs.aws.amazon.com/cli/latest/reference/rds/wait/).

Consulte custos antes do apply e depois do encerramento. Registre fonte,
intervalo de datas, moeda, filtro AWS, valor e erros de permissão. Dados de
custo podem levar pelo menos 24 horas para atualizar. A ausência de linha não
significa custo zero.

Exclua primeiro o snapshot manual e aguarde sua ausência. Só então destrua o
Terraform e confirme que a raiz ficou vazia e os recursos sumiram:

```powershell
aws rds delete-db-snapshot --profile shifu-lab --region us-east-2 --db-snapshot-identifier $snapshotId
aws rds wait db-snapshot-deleted --profile shifu-lab --region us-east-2 --db-snapshot-identifier $snapshotId
terraform -chdir=packages/iac/rds destroy -input=false -auto-approve -no-color
terraform -chdir=packages/iac/rds state list
aws rds describe-db-instances --profile shifu-lab --region us-east-2 --db-instance-identifier $dbId --output json
```

Valide a saída vazia do state e registre `DBInstanceNotFound` na consulta AWS
final. Remova do perfil apenas as variáveis temporárias criadas para essa
execução. Não remova Docker compartilhado nem dados de outros ambientes.

## Registro da execução SHIFU-127

Em 19/11/2026, a conta `565725315792` usou o identificador
`shifu-rds-lab-31b997a3f6`. PostgreSQL 17.9, `db.t4g.micro`, Single-AZ, 20 GB
gp3 criptografados e database `shifu` foram confirmados. A regra de entrada foi
TCP 5432 de `201.75.169.251/32`. O pgvector 0.8.1 estava disponível. As
migrações Alembic reais alcançaram `ad56e779665a`, igual ao único head do código.
O fixture carregou 3 contas, 5 metas e 12 concessões de XP em uma transação. As
contagens persistiram em conexão nova; as três consultas estão no relatório.

O script da aplicação que prepara `shifu_agentos_runtime` tentou alterar um
atributo `SUPERUSER`, negado pelo RDS gerenciado. Após rollback da tentativa,
foi usado DDL compatível com RDS para criar a role sem atributos de superusuário,
definir login/senha e conceder `CONNECT`. Não marque revisões artificialmente.
O `uv` exibiu o aviso de que o `pyproject.toml` na raiz não contém uma tabela
`project`; Alembic concluiu apesar do aviso.

O snapshot manual `shifu-rds-lab-31b997a3f6-manual` chegou a `available` em
2026-11-19T02:49:36.600Z. Ele foi apagado antes da destruição. O Terraform
concluiu `destroy` com cinco recursos removidos. O state list ficou vazio e a
AWS retornou ausência para a instância (`DBInstanceNotFound`), subnet group
(`DBSubnetGroupNotFoundFault`), security group (`InvalidGroup.NotFound`) e
snapshot (`DBSnapshotNotFound`). O arquivo DPAPI da senha e os planos locais
foram removidos; o state vazio permanece local e ignorado pelo Git.

O Cost Explorer foi consultado antes e depois. A consulta posterior, às
03:03 UTC, retornou `Estimated=true`, total diário de US$ 0 e nenhum grupo RDS
para 19/11. A ausência de lançamento não comprova custo zero; aguarde a
atualização financeira. O valor anterior de RDS é agregado à conta e inclui
staging. Consulte [E09](../../../documentation/reports/armazenamento-rds-evidencias/E09-custos-antes-do-encerramento.txt)
e [E11](../../../documentation/reports/armazenamento-rds-evidencias/E11-encerramento-e-ausencia.txt).

Em 20/11/2026, o solicitante dispensou as capturas adicionais de psql e VS Code
Database Client. A conexão TLS usada para migrações, carga e consultas foi
feita por psycopg e está documentada em E07; essa é a evidência de conexão
adotada no escopo final desta execução.

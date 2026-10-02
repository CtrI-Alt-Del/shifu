# Laboratório V1 de armazenamento do Shifu

Este stack Terraform provisiona somente os recursos da V1 da Atividade 3:

- Amazon S3 para objetos fictícios, versionamento e lifecycle;
- Amazon RDS for PostgreSQL para consultas SQL;
- Amazon DynamoDB para eventos de acesso/aprendizagem;
- Amazon EFS, validado por uma EC2 temporária acessada via AWS Systems Manager;
- VPC, sub-redes públicas em duas AZs e Security Groups do laboratório.

Não provisiona nem altera a aplicação Shifu, ECS, ALB, ECR, Redis ou ambientes de staging/produção. Não há endpoints nem integração de storage na API nesta V1. `terraform init`, `terraform validate` e `terraform plan` não criam os recursos AWS; a criação ocorre somente após executar `terraform apply`.

## Pré-requisitos

- Terraform CLI 1.8 ou superior;
- AWS CLI configurado com um perfil que possa criar os recursos do laboratório;
- IP público IPv4 atual do grupo;
- permissão para criar VPC, IAM role/profile, S3, RDS, DynamoDB, EFS, EC2 e Secrets Manager.

Não coloque access keys, senhas, tokens ou arquivos de estado no repositório. A senha mestre do RDS é gerenciada pelo RDS no Secrets Manager. A política pública do S3 exige que as configurações de bloqueio de acesso público no nível da conta permitam a exceção específica do bucket.

## Configuração e validação

Execute no PowerShell, a partir desta pasta:

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
```

Troque `allowed_client_ipv4_cidr` pelo IP público atual do grupo com sufixo `/32`. O exemplo `203.0.113.10/32` pertence a uma faixa reservada para documentação e não permite conexão real.

```powershell
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan
```

Revise o plano, a região e os recursos cobrados antes de aplicar. A região padrão é `us-east-1`; ela pode ser alterada em `terraform.tfvars` e deve ser justificada no relatório. Consulte o AWS Pricing Calculator e o Billing Dashboard: elegibilidade a ofertas gratuitas varia conforme região, conta e uso.

```powershell
terraform apply
```

O estado fica local e é ignorado pelo `.gitignore`. Não o apague enquanto os recursos estiverem ativos: ele é necessário para o Terraform localizar e destruir o que foi criado.

## S3

Gere os arquivos fictícios:

```powershell
python .\scripts\create-fixtures.py
$bucket = terraform output -raw s3_bucket_name
```

Envie imagem, JSON, CSV e TXT privados:

```powershell
aws s3 cp .\fixtures\private\exemplo.svg "s3://$bucket/academic/storage-activity/private/exemplo.svg" --content-type image/svg+xml
aws s3 cp .\fixtures\private\exemplo.json "s3://$bucket/academic/storage-activity/private/exemplo.json" --content-type application/json
aws s3 cp .\fixtures\private\exemplo.csv "s3://$bucket/academic/storage-activity/private/exemplo.csv" --content-type text/csv
aws s3 cp .\fixtures\private\exemplo.txt "s3://$bucket/academic/storage-activity/private/exemplo.txt" --content-type text/plain
```

Envie as duas versões do PDF para a mesma chave:

```powershell
$versionedKey = "s3://$bucket/academic/storage-activity/private/documento-versoes.pdf"
aws s3 cp .\fixtures\private\documento-v1.pdf $versionedKey --content-type application/pdf
aws s3 cp .\fixtures\private\documento-v2.pdf $versionedKey --content-type application/pdf
aws s3api list-object-versions --bucket $bucket --prefix academic/storage-activity/private/documento-versoes.pdf --query "Versions[*].[VersionId,LastModified,IsLatest]" --output table
```

Envie o único objeto público permitido e o CSV que corresponde à regra de lifecycle:

```powershell
aws s3 cp .\fixtures\public\exemplo.txt "s3://$bucket/academic/storage-activity/public/exemplo.txt" --content-type text/plain
aws s3 cp .\fixtures\archive\historico.csv "s3://$bucket/academic/storage-activity/archive/historico.csv" --content-type text/csv
terraform output -raw s3_public_demo_url
```

Abra a URL pública no navegador. A regra de lifecycle move objetos do prefixo `academic/storage-activity/archive/` para `STANDARD_IA` após 30 dias; a transição não é imediata. Versões não atuais são removidas após 90 dias.

## RDS PostgreSQL

O Security Group aceita conexões PostgreSQL somente do IP do grupo (`/32`). O endpoint é roteável publicamente, mas outras origens são bloqueadas pelo Security Group. A senha mestre é gerenciada pelo RDS no Secrets Manager. Consulte o segredo pela Console e use-o no cliente SQL; não inclua a senha em prints ou no relatório.

```powershell
$endpoint = terraform output -raw rds_address
$database = terraform output -raw rds_database_name
$username = terraform output -raw rds_master_username
```

Conecte via DBeaver ou `psql`, porta `5432`, com SSL. O ARN do segredo está disponível em `terraform output -raw rds_master_user_secret_arn`. Execute `sql/schema-and-seed.sql` e depois `sql/queries.sql`. Os scripts criam 10 aprendizes e 15 eventos fictícios e executam `SELECT` com filtro, `JOIN` e `GROUP BY`.

Crie o snapshot manual via Console RDS ou AWS CLI:

```powershell
$instance = terraform output -raw rds_instance_identifier
$snapshot = "$instance-manual-$(Get-Date -Format yyyyMMddHHmm)"
aws rds create-db-snapshot --db-instance-identifier $instance --db-snapshot-identifier $snapshot --region (terraform output -raw aws_region)
aws rds wait db-snapshot-available --db-snapshot-identifier $snapshot --region (terraform output -raw aws_region)
```

Registre o identificador e o status do snapshot. Snapshots manuais ficam fora do ciclo de vida do stack e podem gerar custo após destruir a instância; exclua-os pela Console/CLI se não precisar mantê-los.

## DynamoDB

`user_id` é a Partition Key. `event_key` é a Sort Key e combina timestamp ISO-8601 com ID do evento, por exemplo `2026-09-15T10:00:00Z#event-001`. O GSI `event-type-occurred-at-index` permite consultar eventos por tipo e data sem scan.

Insira os 15 eventos pela AWS CLI:

```powershell
.\scripts\seed-dynamodb.ps1
```

Consulte os eventos de um aprendiz:

```powershell
$table = terraform output -raw dynamodb_table_name
aws dynamodb query --table-name $table --region (terraform output -raw aws_region) --key-condition-expression "user_id = :user" --expression-attribute-values '{":user":{"S":"learner-001"}}'
```

Consulte eventos pelo GSI:

```powershell
aws dynamodb query --table-name $table --index-name event-type-occurred-at-index --region (terraform output -raw aws_region) --key-condition-expression "event_type = :type" --expression-attribute-values '{":type":{"S":"activity_submitted"}}'
```

Registre os comandos e outputs no relatório. Esses dados são sintéticos e não representam o estado oficial de aprendizagem do Shifu.

Para a simulação de escrita, execute:

```powershell
.\scripts\load-test-dynamodb.ps1
```

O padrão gera 1.000 itens em lotes de até 25, distribuídos entre 100 usuários e quatro tipos de evento. A métrica definida é a taxa média de itens gravados por segundo; a meta acadêmica de demonstração é 50 eventos/s. O script informa a taxa observada e se atingiu a meta. Inclua os valores reais (região, volume e duração) no relatório; não trate a meta como garantia de desempenho para produção.

## EFS

O EFS criptografado possui um access point e mount targets em duas AZs. A EC2 de teste não aceita conexões de entrada; use AWS Systems Manager Session Manager. A única regra NFS de entrada do EFS permite o Security Group dessa EC2.

```powershell
terraform output -raw efs_ssm_session_command
```

Execute o comando exibido. Na sessão Linux:

```bash
findmnt /mnt/shifu-storage-lab
printf 'Arquivo de teste persistente do EFS\n' | sudo tee /mnt/shifu-storage-lab/evidencia.txt
sudo cat /mnt/shifu-storage-lab/evidencia.txt
sudo umount /mnt/shifu-storage-lab
sudo mount /mnt/shifu-storage-lab
sudo cat /mnt/shifu-storage-lab/evidencia.txt
```

Capture a montagem e a leitura após remontar. A EC2 é somente um cliente de validação da V1; a API do Shifu não será implantada nem conectada ao EFS nesta etapa.

## Encerramento do laboratório

Depois de coletar as evidências:

```powershell
terraform destroy
```

`force_destroy = true` apaga os objetos S3 e todas as versões do bucket. O destroy também remove a instância RDS, EFS, DynamoDB, EC2, VPC e sub-redes. Snapshots manuais do RDS não são removidos automaticamente. Confira os recursos restantes e o Billing Dashboard.

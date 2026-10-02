# Primeira entrega — laboratório S3 do Shifu

Este pacote Terraform contém somente o laboratório de Amazon S3 da primeira
entrega da atividade de armazenamento. Provisiona um bucket com versionamento,
criptografia, lifecycle e leitura pública restrita a um objeto de demonstração.
Os demais objetos permanecem privados. Os arquivos são fictícios.

## Pré-requisitos

- Terraform CLI >= 1.8 e < 2.0;
- AWS CLI autenticado com permissão para criar e configurar o bucket S3;

A exceção pública precisa ser permitida pelo bloqueio de acesso público da conta.
Não inclua credenciais, estado ou planos no Git. O laboratório não implementa
upload no Mentor e não provisiona RDS, DynamoDB, EFS, EC2 ou VPC.

## Configuração e validação

No PowerShell, a partir de `packages/iac`:

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan
```

Configure a região e o prefixo do bucket. Revise o plano e os custos antes de
executar `terraform apply`. O estado é local e ignorado pelo Git: preserve-o
até remover os recursos. Não é necessário login no Pulumi Cloud.

```powershell
terraform apply
```

## S3

Use os arquivos fictícios já disponíveis em `fixtures/`:

```powershell
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

## Evidências da entrega

Registre nome e região do bucket, cinco tipos de arquivo (SVG, PDF, JSON, CSV
e TXT), a URL pública funcionando, um objeto privado e os identificadores
das duas versões do PDF. Inclua comandos, prints, integrantes e link do
repositório no relatório. A transição de lifecycle é complementar; não ocorre
imediatamente. Não exponha credenciais nas evidências.

## Encerramento do laboratório

Após coletar as evidências e confirmar a remoção:

```powershell
terraform destroy
```

`force_destroy = true` permite remover todos os objetos e versões do bucket.
Confira os recursos restantes na conta. Não use esta configuração pública e
as regras de remoção para anexos reais do Mentor.

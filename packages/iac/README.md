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

O exemplo usa `us-east-2`, região configurada no projeto AWS do grupo. Confirme
a região permitida pela conta e ajuste `terraform.tfvars` quando necessário.
Revise o plano e os custos antes de executar `terraform apply`. O estado é local
e ignorado pelo Git: preserve-o até remover os recursos. Não é necessário login
no Pulumi Cloud.

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
aws s3 cp .\fixtures\private\exemplo.png "s3://$bucket/academic/storage-activity/private/exemplo.png" --content-type image/png
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

## Anexos fictícios no Mentor local

Com o laboratório provisionado, use o adaptador S3 existente da API sem alterar
o código das aplicações. Na mesma sessão PowerShell que iniciará a API,
selecione o perfil válido da conta do grupo e os outputs do laboratório:

```powershell
$env:AWS_PROFILE = 'perfil-da-conta-do-grupo'
$env:MENTOR_ATTACHMENT_STORAGE_BUCKET = terraform output -raw s3_bucket_name
$env:MENTOR_ATTACHMENT_STORAGE_REGION = terraform output -raw aws_region
$env:MENTOR_ATTACHMENT_STORAGE_ADDRESSING_STYLE = 'auto'
```

Substitua o nome de perfil pelo perfil local do grupo. Na configuração local
carregada pela API, inclusive no `.env.local` quando existente, omita os
overrides `MENTOR_ATTACHMENT_STORAGE_ENDPOINT_URL`,
`MENTOR_ATTACHMENT_STORAGE_ACCESS_KEY` e `MENTOR_ATTACHMENT_STORAGE_SECRET_KEY`
usados pelo MinIO. Confirme que também não estão definidos no ambiente do
processo. Assim, o SDK usa o endpoint AWS e a cadeia de credenciais do perfil,
incluindo o token de sessão quando necessário. Preserve a configuração local
anterior para restaurá-la ao final; não copie credenciais para este pacote.

Inicie o Shifu pelos comandos documentados das aplicações e entre no Mentor.
Envie `exemplo.png`, `documento-v1.pdf`, `exemplo.json`, `exemplo.csv` e
`exemplo.txt`, de `fixtures/private/`, em uma mensagem. O Mentor aceita PNG,
JPG, PDF, JSON, CSV e TXT, com no máximo **2.000.000 bytes por arquivo** e
**cinco anexos por mensagem**. Envie `documento-v2.pdf` em outra mensagem se
precisar registrar ambas as revisões no chat.

Registre o envio e a leitura autenticada no Mentor e confirme os objetos no
bucket. Os anexos permanecem privados; somente o TXT na chave pública exata
é a demonstração de acesso anônimo. O Mentor gera uma chave por anexo: os dois
PDFs no chat não substituem a prova de duas versões na mesma chave feita pela
CLI acima. Se a integração exigir alteração no adaptador, registre a limitação
no relatório em vez de modificar o produto. Restaure a configuração local da
API após a coleta e antes de encerrar os recursos do laboratório.

## Evidências da entrega

Registre nome e região do bucket, cinco tipos de arquivo (PNG, PDF, JSON, CSV
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

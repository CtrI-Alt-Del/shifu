# Relatório Técnico — Armazenamento em Nuvem com AWS

## Primeira entrega / Versão 1 — Cenário A: Amazon S3

| Campo | Valor |
| --- | --- |
| Projeto | Shifu |
| Disciplina | Computação em Nuvem II — FATEC |
| Curso | Desenvolvimento de Software Multiplataforma (DSM) |
| Task | SHIFU-126 |
| Status | Laboratório S3 executado e destruído; anexos JSON, CSV e TXT persistiram no Mentor local. O PDF foi rejeitado pelo adaptador e o PNG não concluiu a preparação na interface. A limitação está registrada sem alteração no código da aplicação. |

| Identificação | Informação |
| --- | --- |
| Grupo | Ctrl Alt Del |
| Integrantes informados no esboço | Thiago Martins; Gabriel da Silva; Kauan Fonseca; João Pedro Carvalho; João Gabriel |
| Turma / semestre | DSM — 6º semestre, conforme o esboço existente |
| Esboço original | 01/10/2026 |
| Execução e coleta | 17/11/2026 — America/Sao_Paulo; horários AWS registrados em UTC |
| Data de entrega | Não realizada nesta execução |
| Responsável da task | `gabrielsoliveira1606` |
| Operação técnica | Codex, em execução assistida |
| Conta AWS | `565725315792`; usuário IAM `shifu-storage-lab`; perfil `shifu-lab` |
| Região AWS do projeto | `us-east-2` (Ohio) |
| Bucket criado e removido | `shifu-storage-lab-6dadc912` |
| Repositório | [CtrI-Alt-Del/shifu](https://github.com/CtrI-Alt-Del/shifu) |

O texto distingue configuração, evidência local e resultados observados nos
serviços. O custo aparece como estimativa baseada no saldo de créditos informado
pelo responsável. A descrição da SHIFU-126 foi fornecida pelo usuário; a
consulta ao Jira retornou 404 e a busca retornou 403.

## 1. Contexto e objetivo

O laboratório demonstra um bucket S3, cinco tipos de arquivo, separação de
acesso público e privado, duas versões de um PDF e uma regra de lifecycle. Os
arquivos contêm dados fictícios de estudo. RDS, DynamoDB, produção e mudanças nas
aplicações estão fora do escopo.

A infraestrutura e os passos reproduzíveis estão em
[packages/iac](../../packages/iac/README.md). Os anexos do Mentor foram
experimentados com o Shifu local configurado para o bucket. O comportamento
parcial do adaptador foi registrado sem alterar o produto.

Há uma diferença de redação nas referências: `documentation/infrastructure.md`
ainda descreve o uso do S3 como planejado, enquanto `documentation/architecture.md`
e o adaptador atual registram armazenamento privado implementado. Esta execução
confirma o uso local do adaptador, mas não altera a documentação arquitetural.

## 2. Amazon S3

### 2.1 Configuração e execução

| Configuração | Resultado observado |
| --- | --- |
| Bucket | `shifu-storage-lab-6dadc912` |
| Região | `us-east-2` |
| Versionamento | Ativado |
| Criptografia padrão | SSE-S3, `AES256` |
| Propriedade | `BucketOwnerEnforced`, sem ACLs de objetos |
| Bloqueio público do bucket | ACLs públicas bloqueadas/ignoradas; política pública permitida para a demonstração restrita |
| Política pública | `s3:GetObject` somente para `academic/storage-activity/public/exemplo.txt` |
| Endpoint de demonstração | <https://shifu-storage-lab-6dadc912.s3.us-east-2.amazonaws.com/academic/storage-activity/public/exemplo.txt> |
| Ferramentas | Terraform 1.16.4 (`windows_amd64`); AWS CLI; providers AWS 6.67.0 e Random 3.9.1 conforme lockfile |

O perfil `shifu-lab` autenticou por STS como `arn:aws:iam::565725315792:user/shifu-storage-lab`.
A captura de configurações do projeto indicava `us-east-2`. A primeira tentativa
em `us-east-1` recebeu uma negação explícita da política da organização; com a
região do projeto, o plano de oito recursos foi aplicado com sucesso. A tentativa
inicial não representa o resultado final de permissões da conta.

Foram executados em `packages/iac`:

```powershell
terraform init -backend=false -input=false -lockfile=readonly -no-color
terraform fmt -check -recursive
terraform validate -no-color
terraform plan -input=false -lock=false -no-color -var="aws_region=us-east-2"
terraform apply -input=false -auto-approve -no-color -var="aws_region=us-east-2"
```

A inicialização e as verificações terminaram com código zero; a validação não
emitiu avisos. O plano na região correta previu oito criações e o estado Terraform
confirmou oito recursos durante a coleta. Os outputs registraram a região, o
bucket e a URL pública. Os dados de aplicação e configuração AWS constam de
[E01](armazenamento-s3-evidencias/E01-provisionamento-s3.txt),
[E02](armazenamento-s3-evidencias/E02-validacao-local.txt) e
[E08](armazenamento-s3-evidencias/E08-preflight-aws.txt).

O padrão do laboratório e seu exemplo de `terraform.tfvars` agora usam `us-east-2`,
região confirmada para o projeto do grupo. Ela continua configurável para outros
ambientes.

### 2.2 Arquivos, acesso e anexos do Mentor

Os uploads CLI abaixo foram realizados com fixtures fictícios:

| Fixture | Tipo / tamanho | Chave S3 | Resultado |
| --- | --- | --- | --- |
| `private/exemplo.png` | PNG / 11.239 bytes | `academic/storage-activity/private/exemplo.png` | Upload concluído |
| `private/documento-v1.pdf` | PDF / 616 bytes | `academic/storage-activity/private/documento-versoes.pdf` | Upload concluído; versão anterior |
| `private/documento-v2.pdf` | PDF / 622 bytes | `academic/storage-activity/private/documento-versoes.pdf` | Upload concluído; versão atual |
| `private/exemplo.json` | JSON / 120 bytes | `academic/storage-activity/private/exemplo.json` | Upload concluído |
| `private/exemplo.csv` | CSV / 134 bytes | `academic/storage-activity/private/exemplo.csv` | Upload concluído |
| `private/exemplo.txt` | TXT / 60 bytes | `academic/storage-activity/private/exemplo.txt` | Upload concluído |
| `public/exemplo.txt` | TXT / 56 bytes | `academic/storage-activity/public/exemplo.txt` | Upload concluído; único objeto público |
| `archive/historico.csv` | CSV / 493.543 bytes | `academic/storage-activity/archive/historico.csv` | Upload concluído; elegível para a regra após 30 dias |

O acesso anônimo ao TXT público retornou **HTTP 200** com o conteúdo de
demonstração. O acesso anônimo ao TXT privado retornou **HTTP 403**. Depois de
enviar anexos pelo Mentor, também foi testado anonimamente um objeto sob
`mentor-attachments/`; o S3 retornou `AccessDenied`. Os anexos permanecem
privados e distintos do objeto público do laboratório.

No Mentor local, a API foi configurada temporariamente para o perfil `shifu-lab`,
o bucket acima e a região `us-east-2`, sem overrides do endpoint ou chaves do
MinIO. A interface indicava limite de 2.000.000 bytes por arquivo e até cinco
anexos por mensagem. Resultados observados:

| Tipo | Resultado no Mentor |
| --- | --- |
| JSON | HTTP 201; anexado à mensagem e continuou listado como “Arquivo disponível” após recarregar a conversa |
| CSV | HTTP 201; anexado à mensagem e continuou listado como “Arquivo disponível” após recarregar a conversa |
| TXT | HTTP 201; anexado à mensagem e continuou listado como “Arquivo disponível” após recarregar a conversa |
| PNG | HTTP 201 na tentativa de upload, mas a interface permaneceu em “Preparando arquivo…”; não foi enviado como anexo concluído |
| PDF v1 | HTTP 422, `unsupported_attachment`; não foi anexado. O PDF v2 não foi tentado no Mentor após a rejeição do v1 |

O envio persistido contém três anexos privados (JSON, CSV e TXT), comprovados
após recarregar a conversa. A captura é
[shifu126-mentor-attachments.png](../../apps/web/.playwright-cli/screenshots/shifu126-mentor-attachments.png);
o registro detalhado de respostas, estados e objetos S3 é
[E15](armazenamento-s3-evidencias/E15-mentor-local.txt). A interface confirmou
o vínculo e disponibilidade dos três anexos; não foi feita uma verificação
separada do download autenticado de seus bytes. A resposta de IA não concluiu
nesse ambiente local, embora o envio da mensagem e dos três anexos tenha sido
confirmado.

O PDF é aceito pelo fixture e abre localmente, porém a API respondeu
`unsupported_attachment`. A causa exata não foi confirmada. O PNG recebeu HTTP
201 e ficou travado na preparação da interface. A limitação foi documentada sem
mudança no adaptador ou nas aplicações, como pede o escopo. A listagem final do
bucket mostrou três objetos gerados pelo Mentor, correspondentes aos anexos
persistidos JSON, CSV e TXT.

### 2.3 Versionamento do PDF

Os dois PDFs fictícios têm uma página, conteúdo diferente e hashes locais
registrados em [E09](armazenamento-s3-evidencias/E09-fixtures.txt). Foram
enviados sequencialmente à mesma chave S3:

| Arquivo | Version ID | Última modificação (UTC) | Atual | Tamanho |
| --- | --- | --- | --- | ---: |
| PDF v1 | `NWovtCByPW.GwO.VSEfN0ks3O9pYfEWV` | `2026-11-18T01:33:52+00:00` | Não | 616 bytes |
| PDF v2 | `tcktSUQgy4146Svr2fnDbeu3tRhNNp_c` | `2026-11-18T01:33:54+00:00` | Sim | 622 bytes |

A consulta `list-object-versions` retornou dois identificadores distintos; a
versão v2 era a atual. Os horários da AWS estão em UTC e correspondem à noite de
17/11 em `America/Sao_Paulo`. A saída consta em
[E14](armazenamento-s3-evidencias/E14-s3-validacao.txt).

### 2.4 Regra de lifecycle

A consulta real ao bucket retornou a regra `archive-lab-objects-after-30-days`,
com status `Enabled`, filtro `academic/storage-activity/archive/`, transição
para `STANDARD_IA` após 30 dias e expiração das versões não atuais após 90 dias.
O mínimo configurado para transições é `all_storage_classes_128K`. O fixture
`historico.csv` tem 493.543 bytes, acima de 128 KB.

A configuração foi observada na AWS. A transição e expiração não foram aguardadas
nem são declaradas como ocorridas; os prazos são 30 e 90 dias. Consulte E14 e a
[documentação AWS sobre transições](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html).

### 2.5 Custos

O responsável informou que o saldo de créditos exibido no console passou de
**US$ 112 para US$ 111**, uma redução aparente de aproximadamente **US$ 1**.
Esse valor é uma estimativa baseada no saldo mostrado, sem datas exatas do
intervalo e sem detalhamento por serviço. Ele não permite atribuir a redução
somente ao laboratório. A consulta `ce:GetCostAndUsage` retornou `AccessDenied`
para o usuário `shifu-storage-lab`, sem permissão para o Cost Explorer. O relato
e a resposta da consulta estão em [E11](armazenamento-s3-evidencias/E11-custos.txt).

## 3. Síntese da entrega e remoção

| Item | Resultado | Evidência |
| --- | --- | --- |
| Identidade e conta AWS | Aprovado; conta `565725315792`, usuário IAM `shifu-storage-lab` | E08 |
| Terraform `fmt` e `validate` | Aprovados, sem avisos de validação | E02 |
| Bucket S3 | Criado na região correta e removido ao encerrar | E01, E12 |
| Tipos PNG, PDF, JSON, CSV e TXT no S3 | Upload CLI concluído | E13, E14 |
| Acesso público ao objeto de demonstração | HTTP 200 | E14 |
| Acesso anônimo a objeto privado e anexo do Mentor | HTTP 403 / AccessDenied | E14, E15 |
| Duas versões do PDF | Confirmadas; IDs distintos e v2 atual | E14 |
| Regra lifecycle | Configuração consultada; prazos não transcorreram | E14 |
| Anexos no Mentor | JSON, CSV e TXT persistiram; PNG travou e PDF recebeu 422 | E15 |
| Estimativa pelo saldo de créditos | Redução aparente de ~US$ 1 (US$ 112 → US$ 111); não isolada por serviço | E11 |
| Recursos AWS ao final | Bucket, objetos e configurações removidos via Terraform | E12 |

Após coletar as evidências, `terraform destroy` removeu os oito recursos do
estado do laboratório. A lista posterior não mostrou bucket com o nome usado e
`terraform state list` ficou vazio. O registro inclui o resultado real da
remoção em [E12](armazenamento-s3-evidencias/E12-apply-destroy.txt). O estado e
os planos não foram versionados. Os serviços Docker compartilhados permaneceram
em execução; API, web e sessão de navegador iniciadas para esta coleta foram
encerradas.

**Conclusão:** o laboratório S3 foi criado na região autorizada do projeto,
validado com os oito objetos de estudo e removido. O acesso público ficou restrito
ao objeto de demonstração; objetos privados, inclusive anexos do Mentor, não
permitiram leitura anônima. O versionamento e a regra de lifecycle foram
observados. O Mentor persistiu JSON, CSV e TXT; a falha de PDF e o PNG preso na
preparação permanecem como limitações registradas. O custo total não pôde ser
consultado por falta de permissão do Cost Explorer; o saldo de créditos informado
indica uma redução aproximada de US$ 1, sem permitir atribuí-la apenas ao S3.

## 4. Reflexão do grupo

Estas observações descrevem a execução assistida.

1. A região configurada no projeto AWS precisava ser usada no Terraform; a primeira tentativa em `us-east-1` foi negada, e o laboratório funcionou em `us-east-2`.
2. `terraform fmt -check -recursive` e `terraform validate` passaram sem avisos.
3. O versionamento preservou o PDF v1 ao enviar o v2 para a mesma chave.
4. A política pública permitiu somente o TXT de demonstração; o privado retornou HTTP 403.
5. O S3 confirmou a configuração de lifecycle, mas a atividade não aguardou 30 ou 90 dias para observar ações futuras.
6. O Mentor persistiu os anexos JSON, CSV e TXT após recarregar a conversa.
7. O PDF foi rejeitado e o PNG ficou em preparação; esses resultados foram relatados sem alterar código.
8. O Cost Explorer não permitiu consultar valores para o usuário do laboratório.
9. Terraform removeu o bucket e os recursos ao encerrar o laboratório.

## 5. Referências e continuidade

- Enunciado informado: **Atividade 3 — Relato Armazenamento**, Computação em Nuvem II; descrição da SHIFU-126 fornecida no chat.
- [Procedimentos e fixtures do laboratório](../../packages/iac/README.md).
- [Infraestrutura](../infrastructure.md) e [arquitetura](../architecture.md).
- [Documentação do Amazon S3](https://docs.aws.amazon.com/pt_br/s3/).
- [Considerações sobre lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html).

As capturas do navegador, snapshots e logs usados nesta execução ficam sob
`apps/web/.playwright-cli/{screenshots,snapshots,logs}`. Nenhuma credencial,
chave, estado Terraform, plano ou estado autenticado do navegador foi incluído
nas evidências versionadas. Não houve commit, publicação nem alteração no Jira
ou Confluence.

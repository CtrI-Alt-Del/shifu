# Relatório Técnico — Armazenamento em Nuvem com AWS

## Primeira entrega / Versão 1 — Cenário A: Amazon S3

**Projeto:** Shifu\
**Disciplina:** Computação em Nuvem II\
**Instituição:** FATEC\
**Curso:** Desenvolvimento de Software Multiplataforma (DSM)\
**Status:** esboço; resultados da execução e evidências pendentes.

| Identificação | Informação |
| --- | --- |
| Grupo | Ctrl Alt Del |
| Integrantes | Thiago Martins; Gabriel da Silva; Kauan Fonseca; João Pedro Carvalho; João Gabriel |
| Turma / semestre | DSM — 6º semestre |
| Data de elaboração do esboço | 01/10/2026 |
| Data da entrega | [01/10/2026] |
| Conta AWS | [shifu] |
| Repositório | [CtrI-Alt-Del/shifu](https://github.com/CtrI-Alt-Del/shifu) |
| Commit da configuração utilizada | `221965ac5a4e404096e84cc603637280b213af2d` |
| Bucket criado | [Nome retornado pelo Terraform] |
| URL do arquivo público | [URL retornada por `s3_public_demo_url`] |

> Preencher os campos entre colchetes após a execução. A configuração presente
> no repositório não comprova criação do bucket, upload ou acesso aos arquivos.

A configuração Terraform em `iac`, limitada ao laboratório S3,
está versionada no commit `221965ac5a4e404096e84cc603637280b213af2d`.
Esse registro identifica o código e não comprova implantação na AWS.

## 1. Contexto e objetivo

O Shifu é um sistema de apoio à aprendizagem. Esta primeira entrega investiga
o armazenamento de arquivos na AWS por meio de um laboratório de Amazon S3,
independente da aplicação.

O objetivo é criar um bucket, enviar pelo menos cinco tipos de arquivo,
diferenciar acesso público e privado e demonstrar duas versões de um mesmo
objeto. A configuração também inclui uma regra de lifecycle, descrita no
template sugerido da atividade.

O laboratório [iac](../../iac/README.md) declara a infraestrutura
em Terraform/HCL. Os arquivos fictícios são enviados manualmente pela AWS CLI.
Esta entrega cobre somente o Cenário A; RDS, DynamoDB e a análise comparativa
consolidada pertencem às etapas seguintes.

No projeto, o uso futuro previsto para S3 é armazenar anexos do Mentor. Esse
uso permanece planejado: o laboratório não implementa upload no site nem
conecta arquivos a conversas reais. A política pública da demonstração não é
destinada aos anexos do produto.

## 2. Amazon S3

### 2.1 Configuração do bucket

A configuração define um bucket com nome formado pelo prefixo do projeto e
um sufixo aleatório. A região é parametrizável; o exemplo usa `us-east-1`.
As definições estão em [s3.tf](../../iac/s3.tf).

| Configuração | Definição no código / resultado a registrar |
| --- | --- |
| Nome do bucket | Exemplo configurado: `shifu-storage-lab-<sufixo aleatório>`; nome efetivo: [preencher] |
| Região | `us-east-1` no arquivo de exemplo; região efetivamente usada: [confirmar após execução] |
| Justificativa da região | Proposta: manter uma única região para o laboratório, simplificando sua reprodução. A escolha final e os custos devem ser confirmados pelo grupo. |
| Versionamento | Habilitado na configuração; resultado observado: [preencher] |
| Criptografia padrão | SSE-S3 (`AES256`); resultado observado: [preencher] |
| Propriedade dos objetos | `BucketOwnerEnforced`, sem uso de ACLs |
| Acesso público | Leitura permitida somente ao objeto público de demonstração |
| Estado Terraform | Local, mantido fora do Git |

**Procedimento previsto — terminal Linux/WSL:**

```bash
cd iac
export AWS_PROFILE=shifu
cp terraform.tfvars.example terraform.tfvars
# Ajustar a região e o prefixo em terraform.tfvars.
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan
# Após revisar o plano:
terraform apply
terraform output
```

**Ferramentas verificadas no ambiente local em 01/10/2026:**

| Ferramenta | Versão / ambiente |
| --- | --- |
| Terraform CLI | 1.15.8, `linux_amd64` |
| AWS CLI | 2.37.8, Linux/WSL2 |
| Provider AWS | 6.67.0, registrado em `.terraform.lock.hcl` |

A configuração local foi inicializada com `terraform init -backend=false -input=false`; `terraform fmt -check -recursive` e `terraform validate`
concluíram com sucesso. A validação verifica a configuração, mas não comprova
permissões AWS nem criação de recursos. Não há evidência de `plan` ou `apply`
nesta preparação. O perfil AWS chamado `shifu` não foi encontrado na consulta
local realizada para preencher este esboço; a conta utilizada permanece pendente.

**Registro da execução na AWS:** [Data, integrante responsável, perfil e
conta utilizados e resumo do resultado real. Registrar erros e correções.]

**Evidência E01:** [Print do bucket com nome e região visíveis.]\
**Evidência E02:** [Comandos executados e resultados de validação/aplicação,
sem credenciais ou conteúdo do arquivo de estado.]

### 2.2 Arquivos enviados e permissões

Os arquivos disponíveis em `iac/fixtures` têm conteúdo fictício.
O grupo deve preencher a coluna de confirmação depois de realizar os uploads.

| Arquivo local | Tipo | Chave no bucket | Acesso previsto | Upload confirmado |
| --- | --- | --- | --- | --- |
| `private/exemplo.svg` | Imagem SVG | `academic/storage-activity/private/exemplo.svg` | Privado | [Preencher] |
| `private/documento-v1.pdf` e `private/documento-v2.pdf` | PDF | `academic/storage-activity/private/documento-versoes.pdf` | Privado; duas versões na mesma chave | [Preencher] |
| `private/exemplo.json` | JSON | `academic/storage-activity/private/exemplo.json` | Privado | [Preencher] |
| `private/exemplo.csv` | CSV | `academic/storage-activity/private/exemplo.csv` | Privado | [Preencher] |
| `private/exemplo.txt` | TXT | `academic/storage-activity/private/exemplo.txt` | Privado | [Preencher] |
| `public/exemplo.txt` | TXT | `academic/storage-activity/public/exemplo.txt` | Público | [Preencher] |
| `archive/historico.csv` | CSV | `academic/storage-activity/archive/historico.csv` | Privado; usado no lifecycle | [Preencher] |

O critério é expor somente um arquivo fictício para demonstrar leitura anônima.
A política concede `s3:GetObject` à chave pública específica; não libera
listagem, escrita ou leitura dos objetos privados. As ACLs públicas ficam
bloqueadas. A exceção de política depende também das configurações de bloqueio
de acesso público da conta AWS.

Os comandos individuais de upload estão no
[README do laboratório](../../iac/README.md#cenário-a--amazon-s3).

**Evidência E03:** [Print da listagem com os cinco tipos de arquivo.]\
**Evidência E04:** [URL pública e print do arquivo carregado no navegador.]\
**Verificação complementar E05:** [Resultado do acesso anônimo a um objeto
privado e sua interpretação.]\
**Responsável e data:** [Preencher.]

### 2.3 Versionamento

O Terraform configura o versionamento como `Enabled`. Para demonstrá-lo,
enviar `documento-v1.pdf` e depois `documento-v2.pdf` à mesma chave
`academic/storage-activity/private/documento-versoes.pdf`.

Após os uploads, consultar as versões:

```bash
bucket=$(terraform output -raw s3_bucket_name)
aws s3api list-object-versions \
  --bucket "$bucket" \
  --prefix academic/storage-activity/private/documento-versoes.pdf \
  --query 'Versions[*].[VersionId,LastModified,IsLatest]' \
  --output table
```

| Versão enviada | Version ID | Data/hora registrada | É a versão atual? |
| --- | --- | --- | --- |
| PDF v1 | [Preencher] | [Preencher] | [Preencher] |
| PDF v2 | [Preencher] | [Preencher] | [Preencher] |

**Resultado observado:** [Confirmar duas versões distintas na mesma chave.]\
**Evidência E06:** [Print da aba de versões ou output da CLI com os IDs e
timestamps.]\
**Responsável e data:** [Preencher.]

### 2.4 Regra de lifecycle

A regra configurada aplica-se ao prefixo `academic/storage-activity/archive/`:

| Ação | Prazo configurado |
| --- | --- |
| Transição para `STANDARD_IA` | Após 30 dias |
| Exclusão de versões não atuais nesse prefixo | Após 90 dias |

O arquivo `historico.csv` permite demonstrar o prefixo abrangido pela regra.
Esses prazos não permitem comprovar uma transição imediata durante o
laboratório; o relatório deve distinguir a regra configurada de uma mudança
de classe efetivamente observada.

**Resultado observado:** [Registrar o status e as configurações da regra.]\
**Evidência E07:** [Print da regra, incluindo prefixo, prazo e classe de destino.]\
**Responsável e data:** [Preencher.]

## 3. Síntese da primeira entrega

| Item | Resultado real | Evidência |
| --- | --- | --- |
| Bucket criado, com nome e região identificados | [Pendente / realizado] | E01–E02 |
| Cinco tipos de arquivo enviados | [Pendente / realizado] | E03 |
| Um arquivo público acessível no navegador | [Pendente / realizado] | E04 |
| Pelo menos um arquivo privado identificado | [Pendente / realizado] | E03 / E05 |
| Duas versões do mesmo arquivo | [Pendente / realizado] | E06 |
| Regra de lifecycle documentada | [Pendente / realizado] | E07 |

**Conclusão:** [Resumir os resultados confirmados, o que permanece pendente
e o que foi aprendido sobre objetos, permissões e versionamento.]

**Custos e encerramento:** [Registrar custos observados, período do laboratório
e se o bucket foi mantido ou removido. Não presumir gratuidade. Se houve
remoção, registrar data, responsável e resultado.]

## 4. Reflexão do grupo

[Redigir pelo menos dez linhas, conforme o template. Relatar a divisão das
tarefas, configuração da conta e ferramentas, dificuldades com permissões,
upload, versionamento e lifecycle, soluções adotadas e aprendizados. Usar
experiências reais do grupo; identificar a contribuição dos integrantes.]

| Integrante | Contribuição realizada | Evidências relacionadas |
| --- | --- | --- |
| Thiago Martins | [Preencher] | [Preencher] |
| Gabriel da Silva | [Preencher] | [Preencher] |
| Kauan Fonseca | [Preencher] | [Preencher] |
| João Pedro Carvalho | [Preencher] | [Preencher] |
| João Gabriel | [Preencher] | [Preencher] |

## 5. Referências

- Enunciado e template: **Atividade 3 — Relato Armazenamento**, disponibilizado
  pela disciplina Computação em Nuvem II.
- [Documentação do Amazon S3](https://docs.aws.amazon.com/pt_br/s3/).
- [Configuração e procedimentos do laboratório Shifu](../../iac/README.md).
- [Infraestrutura definida para o Shifu](../infrastructure.md).

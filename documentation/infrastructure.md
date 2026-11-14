# Infraestrutura do Shifu

Este documento registra a **arquitetura de infraestrutura definida** para o
Shifu e o estado atual de cada ambiente.

- **Local:** a pilha de desenvolvimento existe no repositório.
- **Staging:** a plataforma está definida em Terraform no diretório `iac/` e foi
  criada na conta AWS, na região `us-east-2`. Web e API rodam no ECS, com o banco
  populado pelo seed. Funciona só em HTTP, como descrito mais abaixo.
- **Produção:** ainda é só a arquitetura definida neste documento.
- **Laboratório de armazenamento:** tem configuração Terraform em
  `packages/iac`. O código dele não confirma provisionamento na conta AWS.

Para a arquitetura das aplicações e os limites dos módulos de produto, consulte
[`architecture.md`](architecture.md) e [`modules.md`](modules.md).

![Visão simplificada da infraestrutura definida](diagrams/shifu-aws-infrastructure-simplified.png)

## Decisões de plataforma

| Responsabilidade | Escolha para staging e produção |
| --- | --- |
| Provedor de nuvem | AWS |
| Execução das aplicações | Dois serviços ECS com Fargate: Web/BFF e API |
| Banco relacional | Amazon RDS for PostgreSQL |
| Arquivos de anexos do Mentor | Amazon S3; integração planejada, com objetos privados |
| Cache e limitação de requisições | Amazon ElastiCache for Redis, em rede privada, com AUTH e TLS; capacidade de produção a definir |
| Processamento assíncrono | Inngest Cloud |
| E-mail transacional | Resend |
| Avaliação e recursos de IA | OpenRouter, acessado pela API |
| Segredos de aplicação | AWS Secrets Manager |
| Logs, métricas e alarmes AWS | Amazon CloudWatch |
| Provisionamento | Terraform em HCL; staging em `iac/` (com `bootstrap/` para o estado remoto) e laboratório de S3 em `packages/iac`; configuração e estado separados por ambiente |

Essas escolhas não transferem regras de negócio para a infraestrutura. Identity,
Communication, Curriculum, Learning, Gamification e Intelligence continuam com
as responsabilidades definidas em [`modules.md`](modules.md).

## Fluxo das aplicações

```text
Navegador → HTTPS/ALB → Web/BFF (TanStack Start, TypeScript)
                            ├─ Better Auth → RDS PostgreSQL
                            └─ chamadas autenticadas → API (Python, FastAPI)
                                                        ├─ RDS PostgreSQL
                                                        ├─ Redis
                                                        ├─ S3 (anexos privados do Mentor; planejado)
                                                        ├─ Inngest Cloud
                                                        └─ OpenRouter

Inngest Cloud → endpoint assinado da API → jobs → Resend
```

- **Web/BFF:** executa TanStack Start no ECS Fargate. O Better Auth roda no
  processo Web, atende `/api/auth`, mantém contas e sessões no PostgreSQL e
  usa seus segredos de configuração. O BFF chama a API por contrato autenticado;
  a API continua responsável por autorização e regras dos módulos.
- **API:** executa FastAPI no ECS Fargate. A API usa PostgreSQL para dados de
  produto, Redis para cache e limitação de requisições, OpenRouter para os
  recursos de IA previstos e Inngest para trabalho assíncrono.
- **E-mail:** Identity solicita comunicações, Communication organiza a entrega
  assíncrona, e o provedor de produção/staging é o Resend. Better Auth não é um
  serviço de envio de e-mails separado nem chama Resend diretamente nesse fluxo.
- **Inngest:** eventos saem da API para o Inngest Cloud. A plataforma chama o
  endpoint assinado da API para executar as funções registradas. A exposição
  pública desse endpoint deve ser restrita ao caminho necessário e protegida
  pela validação de assinatura.

O ALB recebe tráfego HTTPS e encaminha para os serviços conforme os caminhos
publicados. Web e API devem ter health checks independentes. Os caminhos e
domínios finais de produção serão definidos junto ao roteamento dela.

No staging, o ALB atende HTTP na porta 80 e encaminha tudo para o Web, menos o
caminho `/api/inngest`, que vai para a API. O navegador nunca chama a API
diretamente: o Web/BFF chama a API pela rede privada, no nome
`server.staging.shifu.internal`, porta 7777. A API valida as sessões com as
chaves públicas de assinatura que o Web publica em `/api/auth/jwks`, buscadas no
endereço público do ambiente.

## Rede e sub-redes

Cada ambiente tem uma VPC isolada, distribuída em **duas zonas de
disponibilidade (AZs)**. Em cada AZ:

| Camada | Sub-redes | Recursos e acesso |
| --- | --- | --- |
| Pública | Uma por AZ | ALB e, em produção, NAT Gateway; rota para o Internet Gateway |
| Aplicação | Uma por AZ | Tarefas ECS de Web e API; privada e sem IP público em produção; em staging, rota para o Internet Gateway e IP público, com entrada permitida só pelo ALB |
| Dados | Uma privada por AZ | RDS e Redis; sem rota direta para a internet |

Em produção, cada serviço ECS mantém tarefas nas duas AZs, com capacidade
para continuar atendendo se uma AZ falhar. O RDS usa implantação Multi-AZ.
Staging usa capacidade reduzida e RDS Single-AZ; isso diminui custo e não
oferece a mesma disponibilidade de produção.

As tarefas precisam de saída HTTPS para Inngest Cloud, Resend e OpenRouter. Com
o staging em HTTP puro, a API também precisa de saída na porta 80 para buscar as
chaves de assinatura do Web no endereço público. O security group da API abre
essa porta só nesse modo. Com HTTPS, a busca usa a porta 443 e a regra deixa de
existir.
Produção usa um NAT Gateway por AZ. Staging não tem NAT Gateway, para caber no
orçamento: as tarefas recebem IP público e saem direto pelo Internet Gateway.
Os security groups das tarefas não têm regra de entrada pública; somente o ALB
e, para a API, a Web alcançam as portas das aplicações. Staging também roda em
Fargate Spot com arquitetura ARM64, o que reduz custo e aceita interrupções de
tarefas. As imagens de staging devem ser publicadas para `linux/arm64`. VPC
endpoints para serviços AWS, como ECR, Secrets Manager e CloudWatch, são uma
otimização posterior cuja seleção depende de medição de custo e tráfego.

Os security groups devem permitir somente os fluxos necessários:

- internet → ALB: HTTPS;
- ALB → Web e caminhos públicos necessários da API: portas das tarefas;
- Web/BFF → API: tráfego interno autenticado;
- Web/BFF e API → RDS: PostgreSQL;
- API → Redis: porta do serviço Redis;
- tarefas ECS → serviços AWS e provedores externos: saída necessária.

RDS e Redis não devem aceitar conexões diretamente da internet. O acesso
operacional ao banco deve usar um mecanismo administrativo controlado, sem
abrir a sub-rede de dados.

## Dados, autenticação e segredos

### S3 — anexos do Mentor

O uso definido de S3 no Shifu é **somente para anexos do Mentor**, como imagens,
PDFs e outros arquivos enviados nas conversas. Materiais didáticos não fazem
parte desse uso. A integração com o Mentor é planejada; esta decisão de
infraestrutura não afirma que upload, leitura de anexos ou processamento pela
IA já estejam implementados ou aprovados no PRD de Intelligence.

O S3 guarda o conteúdo dos arquivos. O PostgreSQL guarda seus metadados e
vínculos: identificador do anexo, usuário, conversa, nome original, tipo,
tamanho e chave do objeto. O caminho segue o domínio proprietário:

```text
intelligence/mentor/users/{userId}/conversations/{conversationId}/attachments/{attachmentId}/{filename}
```

Exemplo com identificadores fictícios:

```text
intelligence/mentor/users/u123/conversations/c456/attachments/a789/exercicio.pdf
```

A API deve construir a chave, validar o arquivo e verificar a autorização
para a conversa. O prefixo organiza os objetos, mas não concede acesso. Os
anexos reais permanecem privados, com bloqueio de acesso público no bucket.
A identidade IAM da API deve ter somente as permissões necessárias. Não são
fornecidas credenciais AWS ao navegador.

O fluxo planejado usa URLs pré-assinadas de duração limitada para upload e
download, emitidas após autorização. Antes de disponibilizar o anexo à
conversa, a API deve confirmar o upload e seus metadados. A URL temporária não
é o identificador persistente do arquivo; persiste-se a chave do objeto.
Tipos aceitos, limites de tamanho, retenção, exclusão e integração com a IA
precisam de definição no contrato da funcionalidade antes da implementação.

### Laboratório acadêmico de S3 — primeira entrega

A primeira entrega da atividade de armazenamento é um laboratório separado
da aplicação, operado pela console e/ou CLI, com infraestrutura reproduzível
em Terraform. Não exige implementar o upload no site. O laboratório tem bucket
e estado próprios, sem compartilhar anexos reais com staging ou produção.

O laboratório deve demonstrar:

- criação do bucket, nome e região escolhida;
- pelo menos cinco arquivos de tipos diferentes: imagem, PDF, JSON, CSV e TXT;
- pelo menos um objeto público e um privado;
- versionamento habilitado e duas versões de um objeto na mesma chave;
- link público funcionando no navegador, conforme o template da atividade;
- relatório técnico e link do repositório, com configuração, prints, comandos
  utilizados e identificação dos integrantes.

Os arquivos privados do laboratório usam `academic/storage-activity/private/`
e conteúdos fictícios, conforme o README do pacote. O prefixo de domínio
`intelligence/mentor/` permanece definido para a futura integração do produto.
O objeto público existe somente para a demonstração:

```text
academic/storage-activity/public/exemplo.txt
```

A política do laboratório deve permitir leitura pública apenas desse objeto,
sem liberar listagem, escrita ou leitura dos anexos privados. As configurações
de bloqueio de acesso público da conta e do bucket precisam ser verificadas
para permitir essa exceção. A configuração pública do laboratório não deve
ser aplicada aos buckets de anexos reais.

Para demonstrar versionamento, enviar duas versões de um PDF usando a mesma
chave e registrar os identificadores das versões. Lifecycle e hospedagem de
site estático são complementos sugeridos, não parte obrigatória desta primeira
entrega de S3. O pacote atual contém somente S3 para esta
primeira entrega. Os procedimentos completos estão no
[`README do pacote`](../packages/iac/README.md).

### PostgreSQL e segredos

O PostgreSQL do RDS é compartilhado pelas aplicações conforme seus esquemas e
contratos: Better Auth no Web/BFF persiste contas, sessões e chaves; a API
persiste os dados dos módulos. Migrações de esquema devem ser executadas como
uma etapa controlada do deploy, sem depender da inicialização simultânea das
tarefas. Backups automáticos, retenção, restauração testada e objetivo de
recuperação precisam ser definidos antes de produção.

O Secrets Manager mantém segredos **separados por ambiente**. Os principais
grupos são credenciais do banco, `BETTER_AUTH_SECRET`,
`SHIFU_BFF_SHARED_SECRET`, chaves do Inngest, chave do Resend e credenciais do
OpenRouter. As tarefas ECS recebem somente os segredos necessários à sua
função, por IAM de menor privilégio. O Web/BFF precisa dos segredos do Better
Auth e da integração autenticada com a API; a API precisa dos segredos dos
provedores que utiliza. Nenhum segredo deve ser gravado em imagens, na
configuração Terraform em texto puro ou no repositório.

TLS deve proteger o tráfego público. Exceção temporária do MVP em staging: sem
domínio, o Terraform aceita hostname e certificado ausentes e o ALB atende HTTP
puro no próprio endereço, com cookies seguros desligados por configuração. Senhas
e cookies de sessão trafegam sem criptografia nesse modo, então ele só admite
contas de teste. Produção exige HTTPS. Quando o staging ganhar domínio e
certificado, o modo HTTP e a regra extra de saída na porta 80 deixam de ser
criados. A comunicação entre serviços e com o
banco deve seguir as configurações de criptografia exigidas por cada serviço.
O certificado público pode ser gerenciado pelo AWS Certificate Manager; DNS
e nomes de domínio ainda precisam de definição.

## Processamento, observabilidade e operação

O Inngest Cloud executa os fluxos assíncronos de staging e produção, incluindo
entrega transacional e tarefas com retry. A API deve verificar a assinatura
das chamadas e aplicar idempotência nos jobs que podem ser repetidos. O
Inngest Dev Server continua sendo o ambiente local; testes de integração de
jobs usam a infraestrutura descartável definida no repositório.

Web e API enviam logs e métricas de aplicação ao CloudWatch. ALB e RDS fornecem
métricas de infraestrutura; alarmes devem cobrir indisponibilidade, erros,
latência, capacidade e falhas de jobs. A observabilidade de execução de
funções no Inngest Cloud deve ser consultada na plataforma ou integrada
explicitamente; o CloudWatch não a substitui automaticamente. Logs não devem
conter tokens, credenciais, conteúdo sensível de mensagens ou dados pessoais
desnecessários.

As imagens das aplicações devem ser publicadas no ECR. O pipeline de entrega
deve validar as aplicações, gerar imagens versionadas, executar migrações
controladas e atualizar os serviços ECS com verificação de saúde.

Em staging, dois workflows do GitHub Actions cumprem esse papel.

- **Terraform:** valida e planeja cada mudança em `iac/`. O apply é manual e só
  roda na `main`. Não há ambientes do GitHub nem aprovador obrigatório.
- **Deploy:** a cada merge na `main` que mude as aplicações, gera as imagens
  `linux/arm64` do Web e da API, com a tag do commit, e as publica no ECR. Depois
  roda a migração e o seed do banco como tarefas avulsas do ECS dentro da VPC,
  porque o banco é privado. Então atualiza a API e em seguida o Web, esperando
  cada publicação terminar, e confere a saúde pelo ALB.
- **Seed:** o seed apaga todos os dados da aplicação e recria os dados de
  desenvolvimento, então o staging não guarda contas de teste entre publicações.
  A API só aceita rodá-lo em staging com a opção `SHIFU_ALLOW_STAGING_SEED=true`,
  que só o workflow define. Produção nunca aceita o seed.
- **Falhas e rollback:** se o ECS desfizer a publicação ou ela falhar, o workflow
  falha. O rollback consiste em rodar o workflow de novo com o hash de uma
  publicação antiga, cujas imagens já estão no ECR. Ele não desfaz migrações.
- **Credenciais:** a conta AWS bloqueia OIDC, então o GitHub acessa a AWS com
  chaves de dois usuários IAM de escopo restrito, guardadas como segredos do
  repositório. Um usuário publica as aplicações e o outro roda o Terraform.

Os detalhes de configuração, de operação e de falhas estão em `iac/README.md`.

### Operação do staging

- **Interruptor dos serviços:** a variável `services_enabled` do Terraform define
  quantas tarefas cada serviço roda. Com `false`, ambos ficam em zero e a
  plataforma segue criada, mas sem custo de Fargate. Com `true`, cada serviço roda
  uma tarefa. Serve para a criação em etapas, como parada de emergência e para
  economizar custo. O deploy registra as novas revisões mesmo com os serviços
  desligados, mas só publica e confere a saúde quando eles estão ligados.
- **Task definitions:** o Terraform cria as definições de tarefa. O deploy
  registra novas revisões só com a imagem e a versão trocadas, e os serviços
  ignoram mudanças de definição no Terraform. Assim, um apply não volta um
  serviço para uma imagem antiga.
- **Segredos:** o Terraform cria os segredos vazios no Secrets Manager. O script
  `scripts/populate-staging-secrets.mjs` gera e grava os valores, e ativa o AUTH
  do Redis. Os valores nunca passam pelo Terraform.
- **Tarefas avulsas:** os scripts em `.github/scripts/staging/` rodam a migração,
  o seed e a criação do papel do AgentOS no banco, todos dentro da VPC.

## Ambientes e provisionamento

| Ambiente | Execução e integrações |
| --- | --- |
| Local | `docker-compose.yaml` fornece PostgreSQL, Redis, Inngest Dev Server e Mailpit. Web e API rodam pelos comandos dos respectivos manifests. E-mails são capturados pelo Mailpit. |
| Laboratório | Configuração Terraform em `packages/iac`, somente com S3 e arquivos fictícios para a primeira entrega. Independente do runtime do Shifu. |
| Staging | Em `iac/`, com estado remoto no S3 e segredos próprios. ECS Fargate Spot ARM64, uma tarefa por serviço (0,5 vCPU, 1 GiB) e IP público nas tarefas, sem NAT Gateway. RDS PostgreSQL 17 Single-AZ (`db.t4g.micro`), ElastiCache Redis 7.1 privado (`cache.t4g.micro`), Inngest Cloud e Resend. HTTP puro no endereço do ALB. Dados recriados a cada deploy. |
| Produção | Configuração Terraform, estado e segredos próprios; serviços ECS em duas AZs, RDS Multi-AZ, NAT por AZ, Inngest Cloud e Resend. |

Terraform deve criar e atualizar os recursos AWS de cada ambiente, inclusive
rede, grupos de segurança, IAM, ECR, ECS, ALB, banco, cache, S3, segredos e
observabilidade. Os ambientes precisam de configuração e estado isolados. A
revisão de mudanças de infraestrutura deve preceder a aplicação em produção.
Inngest Cloud, Resend e OpenRouter são serviços externos configurados por
ambiente; o Terraform provisiona a infraestrutura AWS, não esses serviços por
inferência.

### Organização do Terraform do staging

O staging fica no diretório `iac/`, com duas raízes Terraform independentes.

- `iac/bootstrap/`: cria só o bucket S3 privado que guarda o estado remoto.
- `iac/staging/`: cria a plataforma da aplicação. Os arquivos separam rede
  (`network.tf`), segurança (`security.tf`), ALB (`alb.tf`), banco e cache
  (`data.tf`), ECS (`compute.tf`), ECR (`ecr.tf`), segredos (`secrets.tf`), IAM
  e usuários de CI (`iam.tf`, `ci.tf`) e orçamento (`operations.tf`).

Cada raiz tem testes com provedor simulado, em arquivos `*.tftest.hcl`, que o
workflow do Terraform roda em cada pull request. Os valores privados ficam em
`terraform.tfvars` e `backend.hcl`, ignorados pelo Git. No CI, o conteúdo do
`terraform.tfvars` vem de um segredo do repositório codificado em base64. O passo
a passo completo está em `iac/README.md`.

### Organização do pacote do laboratório

O pacote do laboratório fica em `packages/iac`, com recursos declarados em HCL e somente
Amazon S3 para a primeira entrega da atividade. Os arquivos fictícios são
enviados manualmente pela AWS CLI, conforme o README; não há script de fixtures.

```text
packages/iac/
├── README.md
├── .gitignore
├── .terraform.lock.hcl
├── versions.tf
├── variables.tf
├── locals.tf
├── outputs.tf
├── terraform.tfvars.example
├── s3.tf
└── fixtures/
    ├── public/
    ├── private/
    └── archive/
```

- `versions.tf`: versões aceitas do Terraform e providers AWS e Random.
- `.terraform.lock.hcl`: versões e hashes dos providers; deve ser versionado.
- `variables.tf` e `terraform.tfvars.example`: região AWS e prefixo do bucket.
- `locals.tf`: tags compartilhadas do laboratório.
- `s3.tf`: bucket, versionamento, criptografia, lifecycle e política pública
  restrita ao objeto de demonstração.
- `outputs.tf`: região, nome do bucket e URL pública de demonstração.
- `fixtures/`: arquivos fictícios para upload manual, incluindo duas versões
  do PDF.

O pacote é um laboratório acadêmico de S3. Não provisiona rede, RDS, DynamoDB,
EFS ou serviços da aplicação e não implementa anexos do Mentor. A arquitetura
de staging e produção continua planejada, com configuração e estado próprios.

### Estado e execução

O staging usa estado remoto no bucket S3 criado por `iac/bootstrap`, com bloqueio
por arquivo (`use_lockfile`). O laboratório de S3 em `packages/iac` usa estado
local, ignorado pelo `.gitignore`. A identidade AWS é fornecida pelas
credenciais ou pelo perfil do operador. Credenciais, arquivos de estado e planos gerados não
entram no Git; o estado deve ser preservado enquanto houver recursos ativos.

A partir de `packages/iac`, o fluxo documentado no README é:

```sh
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan
```

A criação de recursos ocorre com `terraform apply`, após revisão do plano e
autorização para a implantação. Para o staging, o fluxo equivalente roda a partir
de `iac/staging` e está em `iac/README.md`. A decisão anterior de usar Pulumi
Cloud foi substituída. Produção ainda precisa de backend remoto e controle de
acesso próprios.

O código do laboratório existe no pacote. O documento não confirma execução
de `apply` do laboratório nem provisionamento de recursos dele na conta AWS.

## Parâmetros de implementação antes do primeiro deploy

- Região AWS, domínios, certificados e política de DNS/WAF.
- CIDRs da VPC, endereçamento das sub-redes e estratégia de acesso operacional.
- Produto Redis gerenciado, dimensionamento inicial e política de persistência.
- Capacidade mínima ECS por ambiente, autoscaling e limites de custo.
- Retenção de backups e logs, testes de restauração, RPO e RTO. No staging, os
  backups automáticos do RDS ficam desligados (retenção zero), porque o plano
  gratuito da AWS recusa a retenção de sete dias.
- Pipeline de deploy, migrações, rollback e estado remoto de produção. O staging
  já os tem.
- Domínio e certificado do staging, para sair do HTTP puro.
- Uso de VPC endpoints frente ao custo de NAT e volume de saída.

Esta arquitetura complementa a arquitetura da aplicação. Os parâmetros
operacionais acima não alteram as escolhas de plataforma definidas neste
documento. Nomes exatos de recursos, preços e capacidades de produção serão verificados
durante a implementação do Terraform dela. Este documento só afirma que o
staging está provisionado.

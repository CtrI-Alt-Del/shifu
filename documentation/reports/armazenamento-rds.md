# Relatório Técnico — Armazenamento em Nuvem com AWS

## Entrega final — Cenário B: Amazon RDS

| Campo | Valor |
| --- | --- |
| Projeto | Shifu |
| Disciplina | Computação em Nuvem II — FATEC |
| Curso | Desenvolvimento de Software Multiplataforma (DSM) |
| Task | SHIFU-127 |
| Status | Concluído conforme escopo final autorizado em 20/11/2026. A instância foi configurada, as migrações reais chegaram ao head, os 20 registros fictícios persistiram, as consultas TLS foram executadas, o snapshot foi criado e removido e `terraform destroy` removeu os cinco recursos. A conexão foi validada por psycopg; capturas adicionais de psql e VS Code foram dispensadas pelo solicitante. |

| Identificação | Informação |
| --- | --- |
| Grupo | Ctrl Alt Del |
| Responsável pela coleta | Gabriel da Silva |
| Operação técnica | Codex, execução assistida |
| Conta AWS esperada | `565725315792` |
| Perfil | `shifu-lab` |
| Região | `us-east-2` (Ohio) |
| Data da preparação local | 18/11/2026 — America/Sao_Paulo |
| Tentativa AWS | 18/11/2026, plano revisado; aplicação parcial bloqueada e recursos parciais removidos |
| Retomada AWS | 18/11/2026, 21:44–21:47 America/Sao_Paulo; dry-run negado sem criar recursos, conforme E04 |
| Segunda aplicação | 19/11/2026, 01:42 UTC (18/11, 22:42 America/Sao_Paulo); instância criada, conforme E06 |
| Rotação, migrações e carga | 19/11/2026, aproximadamente 02:30–02:45 UTC (18/11, 23:30–23:45 America/Sao_Paulo), conforme E07 |
| Snapshot manual | Criado às 02:49:36.600 UTC de 19/11/2026; `available`, conforme E08 |
| Data de entrega | 20/11/2026 — concluído conforme escopo final autorizado pelo solicitante |
| Endpoint e identificador RDS | `shifu-rds-lab-31b997a3f6`; `shifu-rds-lab-31b997a3f6.cvge4eks0bg1.us-east-2.rds.amazonaws.com` |
| Repositório | [CtrI-Alt-Del/shifu](https://github.com/CtrI-Alt-Del/shifu) |

## 1. Contexto e objetivo

O Cenário B demonstra Amazon RDS com PostgreSQL 17 espelhando a configuração
de staging, migrações Alembic reais, dados fictícios em tabelas reais e consultas
SQL. A rede e o estado Terraform são próprios do laboratório. Staging não é
alterado.

A infraestrutura e os passos reproduzíveis estão em
[packages/iac/rds](../../packages/iac/rds/README.md). Os dados de demonstração
usam `identity_accounts`, `learning_goals` e `gamification_xp_grants`. O SQL não
cria sessões nem tokens, e usa contas sem credenciais utilizáveis.

Na primeira tentativa, o perfil `shifu-lab` não permitiu consultar a rede, o
RDS ou custos; isso está registrado em [E02](armazenamento-rds-evidencias/E02-tentativa-execucao-bloqueada.txt).
Após a atualização de permissões, STS confirmou a conta `565725315792`, a VPC
padrão `vpc-0420e74cba45bc0a9`, DNS habilitado e três sub-redes padrão nas zonas
`us-east-2a`, `us-east-2b` e `us-east-2c`, com rota ativa para Internet Gateway.
PostgreSQL 17 em `db.t4g.micro` apareceu como opção. O primeiro apply foi
bloqueado por `ec2:CreateSecurityGroup`, conforme E03. Na segunda tentativa, o
dry-run foi autorizado e o plano revisado tinha cinco criações. O apply inicial
criou identificador, grupo de sub-redes e security group, mas parou ao revogar
a saída padrão; a limpeza dessa tentativa foi confirmada em E05. Após as
permissões EC2, o apply seguinte criou a instância PostgreSQL e a regra de
entrada restrita. Após o usuário atualizar a política IAM com
`rds:ModifyDBInstance`, a rotação da senha foi aplicada em atualização in-place.
As migrações e a carga fictícia concluíram. Staging permaneceu intacto.

## 2. Amazon RDS

### 2.1 Configuração prevista e estado observado

| Configuração | Especificação | Resultado observado |
| --- | --- | --- |
| Região | `us-east-2` | Instância consultada em Ohio |
| Engine | PostgreSQL 17 | PostgreSQL `17.9` |
| Classe | `db.t4g.micro` | Confirmada pela API RDS |
| Banco | `shifu` | Confirmado pela API RDS |
| Disponibilidade | Single-AZ | `MultiAZ=false`; zona `us-east-2c` |
| Armazenamento | 20 GB gp3, criptografado | Confirmado: 20 GB, gp3, criptografado |
| Endereço | Público, somente IPv4 do integrante `/32` | Público; SG `sg-0fda2bc319b7f32ed` permite TCP 5432 somente de `201.75.169.251/32` |
| TLS | `sslmode=require` nas conexões | Confirmado em conexão psycopg ao endpoint RDS |
| Retenção de backup automático | 0 dias | Confirmada pela API RDS |
| Snapshot final automático | Desativado | `skip_final_snapshot=true`; exclusão desprotegida para limpeza |
| Snapshot manual | Criado, validado e removido | `shifu-rds-lab-31b997a3f6-manual`; `available` às 02:49:36.600 UTC; depois removido, ver E08 e E11 |

O Terraform usa uma raiz isolada em `packages/iac/rds` e consulta a VPC padrão.
A pré-verificação exige DNS habilitado, sub-redes em pelo menos duas zonas e
rotas ativas para Internet Gateway. Nenhuma VPC, sub-rede ou rota de staging é
usada pelo laboratório.

O sufixo aleatório torna o identificador exclusivo por execução. A senha mestre
é fornecida pelo atributo write-only do provider e não é exportada por output,
nem armazenada no state ou no plano. A senha da primeira criação foi removida
da memória ao final do apply. Após a atualização IAM informada pelo usuário, a
versão write-only 5 foi aplicada com atualização in-place e sem recriar a
instância. O valor não é exibido neste relatório.

### 2.2 Migrações, amostra e consultas

O código usado contém 45 revisões Alembic e um único head,
`ad56e779665a`. `uv run alembic upgrade head` foi executado no banco novo com
`DATABASE_URL` apontando explicitamente para o endpoint de laboratório. Uma
conexão nova confirmou `ad56e779665a (head)`, igual ao head do código.

O servidor disponibilizou pgvector `0.8.1`. O script existente para preparar
`shifu_agentos_runtime` tentou alterar o atributo `SUPERUSER`, operação que a
role mestra gerenciada pelo RDS não pode executar. Após o erro e rollback, a
role foi criada com atributos compatíveis com RDS por DDL equivalente. As
migrações reais então concluíram. Nenhum `.env` das aplicações foi carregado.

O fixture SQL versionado carregou em uma única transação 3 contas pendentes com
e-mails `.invalid`, 5 metas e 12 concessões fictícias de XP. A contagem total
foi 20. As contagens foram conferidas em conexão nova. Não foram criadas
credenciais utilizáveis, sessões ou tokens.

| Consulta | Resultado observado |
| --- | --- |
| Filtro `learning_goals.title ILIKE '%SQL%'` | 5 metas: SQL básico; Consultas SQL; JOIN em SQL; PostgreSQL inicial; GROUP BY SQL |
| JOIN entre `identity_accounts` e `gamification_xp_grants` | 12 concessões, todas associadas às três contas fictícias; resultado completo em E07 |
| GROUP BY por conta | Conta fictícia 03: 4 concessões / 185 XP; conta 01: 4 / 150 XP; conta 02: 4 / 140 XP |
| Contagem persistida em nova conexão | 3 contas, 5 metas e 12 concessões de XP |

As migrações reais concluíram; não foi necessário usar o schema de fallback
`rds_lab`. O SQL, as saídas completas e a observação de persistência estão em
[E07](armazenamento-rds-evidencias/E07-migracoes-carga-consultas.txt).

### 2.3 Acesso por clientes e snapshot

O endpoint respondeu em TCP/5432 e as operações de migração, carga e consulta
usaram TLS (`sslmode=require`) por psycopg. Os resultados estão em E07. Em
20/11/2026, o solicitante dispensou as capturas adicionais por psql e VS Code
Database Client. A conexão técnica é comprovada pelas operações realizadas
contra o endpoint RDS.

| Evidência | Estado |
| --- | --- |
| Conexão TLS ao endpoint | Executada por psycopg para pgvector, Alembic, carga e consultas; E07 |
| Capturas adicionais por psql e VS Code Database Client | Dispensadas pelo solicitante em 20/11/2026 |
| Snapshot manual, identificador/status/horário UTC | Criado como `shifu-rds-lab-31b997a3f6-manual`, `available` às 02:49:36.600 UTC e removido; E08 e E11 |

O snapshot foi criado depois da carga e das consultas e removido antes de
`terraform destroy`, conforme E08 e E11.

### 2.4 Custos

Em 18/11/2026, antes do primeiro apply, e novamente antes da segunda tentativa,
o Cost Explorer respondeu para o serviço Amazon Relational Database Service,
métrica `UnblendedCost` em USD, granularidade diária, período de 2026-11-10 a
2026-11-18 (limite final exclusivo). Os totais foram US$ 0,0000000495 em
10–11/11 e US$ 0,0000000502 em cada dia de 11–12/11 a 17–18/11. Na consulta
antes do segundo apply, 18–19/11 também apareceu estimado:
`USE2-InstanceUsage:db.t4g.micro` US$ 0;
`USE2-RDS:GP3-Storage` US$ -0,0000000039; tráfego de entrada US$ 0; saída
inter-regional `USE2-USE1-AWS-Out-Bytes` US$ 0,0000000329. A consulta de
19/11 às 02:01 UTC (18/11 às 23:01 em `America/Sao_Paulo`), já após a criação
da instância, retornou para 18–19/11: `db.t4g.micro` US$ 0,
GP3 US$ -0.0000000039, entrada US$ 0 e saída inter-regional US$
0.0000000329; soma por uso US$ 0.0000000290. `Estimated=true`. O filtro cobre
todo o serviço RDS da conta, inclusive staging, e não permite atribuir esse
valor ao laboratório. Na consulta de 19/11 às 02:52 UTC (18/11 às 23:52 em
`America/Sao_Paulo`), o Cost Explorer ainda retornou `Estimated=true`: para
18/11 repetiu US$ 0,000000029 agregado de RDS; para 19/11 não retornou grupo
RDS e o total diário apareceu como US$ 0. Essa linha ausente não é custo zero.
O Cost Explorer pode levar 24 horas ou mais para atualizar. Os retornos não
são custo final nem permitem separar laboratório de staging. Após o destroy,
a consulta de 19/11 às 03:03 UTC ainda retornou `Estimated=true`, total diário
US$ 0 e sem grupo de serviço RDS; isso não prova custo zero. Veja E09 e E11.
Consulte também
[E03](armazenamento-rds-evidencias/E03-aplicacao-parcial-e-limpeza.txt),
[E04](armazenamento-rds-evidencias/E04-retomada-permissoes.txt),
[E05](armazenamento-rds-evidencias/E05-apply-parcial-e-limpeza.txt) e E06.

### 2.5 Evidências e validação local

| Evidência | Resultado |
| --- | --- |
| E00 — identidade e pré-verificação AWS | Histórico da primeira tentativa, antes da liberação de leitura |
| Terraform fmt, validate e testes locais | Aprovados após baixar os providers; ver E01 |
| E02 — tentativa AWS em 18/11/2026 | Histórico da primeira tentativa, com negações de leitura e custo |
| E03 — plano, apply parcial e limpeza | Cinco criações planejadas; falha em `ec2:CreateSecurityGroup`; recursos parciais removidos; state vazio e ausência remota confirmada |
| E04 — retomada após atualização das políticas | Rede e IP confirmados; Cost Explorer respondeu; dry-run de `CreateSecurityGroup` negado; state e recursos do laboratório continuam ausentes |
| E05 — segunda aplicação e limpeza | Dry-run autorizado; apply bloqueado em `RevokeSecurityGroupEgress`; destroy bloqueado em `DescribeNetworkInterfaces`; exclusão direta do SG, state vazio e ausência remota confirmados |
| E06 — criação e histórico de IAM | Registra a instância e as tentativas inicialmente negadas; a política foi atualizada depois, e a rotação v5 concluiu |
| E07 — migrações, carga e consultas | Head Alembic aplicado, 20 linhas fictícias persistidas e resultados completos das três consultas |
| E08 — snapshot manual | Snapshot `available`, com id e timestamp AWS em UTC |
| E09 — custos antes do encerramento | Cost Explorer diário, estimado, agregado e sem atribuição exclusiva ao laboratório |
| E10 — configuração e rotação confirmadas | RDS e regra `/32` verificados; atualização de senha in-place concluída |
| E11 — encerramento e ausência | Snapshot removido; cinco recursos destruídos; state vazio e ausências AWS confirmadas; custo pós-destroy observado |

As validações locais foram `terraform fmt -check -recursive`,
`terraform validate` e `terraform test`: configuração válida, dois testes
aprovados e nenhuma falha. O plano de rotação v5 continha apenas uma atualização
in-place. Os comandos `uv run alembic ...` concluíram, mas `uv` emitiu o aviso
`pyproject.toml does not contain a project table` para o `pyproject.toml` da
raiz. Isso não impediu as migrações e não foi suprimido.

## 3. Síntese da entrega e remoção

| Item | Resultado | Evidência |
| --- | --- | --- |
| Conta/perfil AWS | Conta `565725315792` autenticada; permissões de rede/RDS usadas; rotação v5 concluída | E03–E06 |
| Terraform RDS | Cinco recursos removidos; state vazio; nenhum vínculo ao state de staging | E10–E11 |
| Instância RDS | PostgreSQL 17.9 foi `available`, configuração conferida e regra `/32`; instância removida | E10–E11 |
| Migrações Alembic | Aplicadas até `ad56e779665a`, igual ao head do código | E07 |
| Vinte registros fictícios | 3 contas, 5 metas e 12 concessões de XP persistidas | E07 |
| Consultas SQL | Filtro, JOIN e GROUP BY executados; saídas completas registradas | E07 |
| Conexão ao banco | TLS por psycopg comprovada; capturas adicionais dispensadas pelo solicitante | E07, E10 e E11 |
| Snapshot manual | `available` às 02:49:36.600 UTC; removido antes da limpeza | E08 e E11 |
| Custos | Consultas anteriores e posteriores ao destroy registradas; dados estimados, agregados ou sem lançamento RDS; valor final ainda pode atualizar | E03–E06, E09 e E11 |
| `terraform destroy` e remoção do snapshot | Concluídos; state vazio e recursos ausentes na AWS | E11 |

**Conclusão:** o laboratório espelhou a configuração solicitada e usou
a rede padrão somente como dependência de leitura. A regra TCP 5432 permitia
somente `201.75.169.251/32`. A rotação de senha concluiu após a política IAM
ser atualizada. O pgvector foi confirmado e as 45 migrações chegaram ao head
`ad56e779665a`. Foram persistidos e consultados 20 registros fictícios em tabelas
reais. O snapshot manual chegou a `available` e foi removido. `terraform destroy`
removeu os cinco recursos. As verificações AWS retornaram ausência para a
instância, subnet group, security group e snapshot; o state ficou vazio.

Em 20/11/2026, o solicitante dispensou as capturas adicionais por psql e VS Code
Database Client; por isso, a conexão via psycopg/TLS registrada em E07 é a
evidência de conexão usada nesta entrega. O Cost Explorer foi consultado após a
remoção, mas os dados ainda estão estimados e agregados; nenhuma ausência de
lançamento foi descrita como custo zero. Staging e aplicações não foram
alterados. State, plano e segredo local não foram versionados.

## 4. Referências e continuidade

- Descrição da SHIFU-127 fornecida na solicitação da tarefa; o Jira retornou 404.
- [Laboratório Terraform e comandos RDS](../../packages/iac/rds/README.md).
- [Infraestrutura do Shifu](../infrastructure.md) e
  [arquitetura](../architecture.md).
- [Documentação do Amazon RDS para PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html).
- [Custos no Cost Explorer](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-enable.html).

O relatório técnico e o laboratório foram concluídos conforme o escopo final
autorizado pelo solicitante em 20/11/2026. As evidências e o procedimento
operacional estão no [README do laboratório](../../packages/iac/rds/README.md).

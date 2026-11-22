# Laboratório DynamoDB do Shifu

Laboratório acadêmico isolado da aplicação. Usa apenas eventos fictícios. Não
configure esta raiz para apontar a uma tabela de produto.

## Pré-requisitos e identidade

- Terraform 1.8 ou posterior e AWS CLI v2.
- Perfil AWS `shifu-lab` na conta `565725315792`, região `us-east-2`.
- Acesso IAM a DynamoDB nesta tabela e ao CloudWatch para consultar as métricas.
- O operador técnico da coleta é **Gabriel da Silva**, com execução assistida
  por Codex. O nome do perfil IAM identifica a credencial; o nome acima registra
  o integrante responsável pelo procedimento.

Em 20/11/2026, a primeira pré-verificação negou leitura de DynamoDB e métricas
do CloudWatch. O responsável então associou a política gerenciada
`ShifuDynamoDbLabAccess` ao usuário `shifu-storage-lab`; STS, Terraform, as
consultas e o CloudWatch funcionaram com o perfil `shifu-lab`. O documento
`administrator-policy.json` é uma referência mínima para futuras execuções.
Ele limita alterações às tabelas com prefixo `shifu-dynamodb-lab-`; a leitura
de métricas do CloudWatch exige `Resource: "*"` pela API AWS.

## Recursos e modelo

Terraform cria uma tabela `PROVISIONED` com capacidade 5 RCU/5 WCU e GSI com 5
RCU/5 WCU, criptografia gerenciada pelo DynamoDB, sem PITR e sem proteção contra
remoção. O estado fica local e os arquivos de estado, planos e variáveis locais
são ignorados pelo Git. Não versionar credenciais, `.tfvars`, estado nem planos.

Chaves:

- Tabela: `PK=LEARNER#<id>`, `SK=<timestamp ISO-8601 UTC>#<event_id>`.
- `EventTypeDayIndex`: `GSI1PK=EVENT#<event_type>#<YYYY-MM-DD UTC>` e
  `GSI1SK=<timestamp UTC>#<learner_id>#<event_id>`.
  O índice usa projeção `KEYS_ONLY` para limitar atributos duplicados.

O item preserva `event_type`, `event_id`, `learner_id`, `occurred_at` e um mapa
`attributes`. Apenas as chaves de tabela e de índice têm declaração de tipo no
Terraform. Os vinte itens em `fixtures/events.json` variam tipos e atributos.
Todos são fictícios. Os cinco nomes de eventos não afirmam contratos atuais do
Shifu.

## Execução

Inicialize e valide antes de aplicar:

```bash
export AWS_PROFILE=shifu-lab
terraform init -backend=false -input=false -lockfile=readonly
terraform fmt -check -recursive
terraform validate -no-color
terraform plan -input=false -lock=false -no-color -var="aws_region=us-east-2"
```

Com o perfil acima e as permissões IAM necessárias, revise o plano e aplique:

```bash
terraform apply -input=false -no-color -var="aws_region=us-east-2"
```

`scripts/lab.sh` obtém o nome da tabela pelo output Terraform. Por padrão usa o
perfil `shifu-lab` e grava resultados locais em `evidence-local/`, ignorado pelo
Git. Esses resultados devem ser inspecionados e copiados para a pasta de
evidências do relatório somente depois de conferidos e sem credenciais.
No Windows, o wrapper prefere o ambiente Python 3.13 já instalado em
`apps/server/.venv`; em outro ambiente pode-se escolher um executável com
`PYTHON_BIN`.

```bash
bash -n scripts/lab.sh
bash scripts/lab.sh validate-fixtures
bash scripts/lab.sh load
bash scripts/lab.sh query --learner learner-001 --event-type xp_granted --event-date 2026-11-18
bash scripts/lab.sh simulate
```

A carga inicial escreve exatamente os itens da fixture. A consulta busca um item
por chave, lista o histórico de um aprendiz por PK e consulta o GSI por tipo e
dia. A simulação grava sessenta novos eventos com um segundo entre escritas,
contabiliza a duração e o `ConsumedCapacity` retornado pela AWS CLI e produz
`simulation-results.json`. Ela é uma simulação simbólica de atividade, não um
teste de limite de throughput do serviço.

Passe os horários UTC da simulação para a consulta de métrica:

```bash
bash scripts/lab.sh metrics --start-time '<start_time_utc>' --end-time '<end_time_utc>' --expected-table-units 60 --expected-gsi-units 60
```

O coletor pede `AWS/DynamoDB:ConsumedWriteCapacityUnits`, estatística `Sum`,
período de 60 segundos, com dimensão `TableName` e separadamente com
`TableName` + `GlobalSecondaryIndexName=EventTypeDayIndex`. A média observada de
unidades/s em cada minuto é `Sum / 60`. O coletor aguarda até 15 minutos,
incluindo dois minutos após o último período, e compara as somas da janela com o
`ConsumedCapacity` retornado por `PutItem`. Falta de datapoints ou divergência
permanece pendente; nunca é interpretada como zero ou aprovação.

## Encerramento

Consulte custos na conta antes e depois, registrando período, moeda e se são
estimados. Depois remova os recursos:

```bash
TABLE_NAME="$(terraform output -raw table_name)"
terraform destroy -input=false -no-color -var="aws_region=us-east-2"
terraform state list
aws dynamodb describe-table --table-name "$TABLE_NAME" --profile shifu-lab --region us-east-2
```

O último comando deve retornar `ResourceNotFoundException`, que confirma que a
tabela não existe. Guarde o state local até confirmar a remoção. Na execução
registrada em 20/11/2026, a tabela já foi destruída e o state tem zero recursos
gerenciados. Para repetir o laboratório, aplique novamente o Terraform antes
de carregar eventos. Não publique evidências contendo credenciais.

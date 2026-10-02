param(
    [Parameter(Mandatory = $true)]
    [string]$Operator,
    [string]$Region
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Operator)) {
    throw "Informe o nome do integrante que executa o seed usando -Operator."
}
$moduleDirectory = Split-Path -Parent $PSScriptRoot
$fixturePath = Join-Path $moduleDirectory "fixtures\dynamodb-events.json"

if (-not $Region) {
    $Region = (& terraform "-chdir=$moduleDirectory" output -raw aws_region).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Nao foi possivel ler o output aws_region do Terraform."
    }
}

$tableName = (& terraform "-chdir=$moduleDirectory" output -raw dynamodb_table_name).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Nao foi possivel ler o output dynamodb_table_name do Terraform."
}

$items = @(Get-Content -LiteralPath $fixturePath -Raw | ConvertFrom-Json)
$pendingRequests = @(
    $items | ForEach-Object {
        @{ PutRequest = @{ Item = $_ } }
    }
)
$temporaryFile = Join-Path ([System.IO.Path]::GetTempPath()) "shifu-dynamodb-seed-$([guid]::NewGuid().ToString('N')).json"

try {
    $retryCount = 0
    while ($pendingRequests.Count -gt 0) {
        $payload = @{ $tableName = $pendingRequests } | ConvertTo-Json -Depth 20 -Compress
        [System.IO.File]::WriteAllText(
            $temporaryFile,
            $payload,
            [System.Text.UTF8Encoding]::new($false)
        )

        $responseText = & aws dynamodb batch-write-item --request-items "file://$temporaryFile" --region $Region --output json
        if ($LASTEXITCODE -ne 0) {
            throw "AWS CLI nao conseguiu inserir os itens de exemplo no DynamoDB."
        }

        $response = ($responseText -join [Environment]::NewLine) | ConvertFrom-Json
        $tablePendingProperty = $response.UnprocessedItems.PSObject.Properties[$tableName]
        if ($tablePendingProperty) {
            $pendingRequests = @($tablePendingProperty.Value)
        }
        else {
            $pendingRequests = @()
        }

        if ($pendingRequests.Count -gt 0) {
            $retryCount++
            if ($retryCount -gt 8) {
                throw "O DynamoDB continuou retornando itens nao processados apos oito tentativas."
            }
            Start-Sleep -Seconds 2
        }
    }
}
finally {
    Remove-Item -LiteralPath $temporaryFile -Force -ErrorAction SilentlyContinue
}

Write-Output "Tabela: $tableName"
Write-Output "Itens inseridos: $($items.Count)"
Write-Output "Regiao: $Region"
Write-Output "Integrante responsavel: $Operator"

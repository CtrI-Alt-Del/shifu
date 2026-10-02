param(
    [string]$Region
)

$ErrorActionPreference = "Stop"
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
$putRequests = @(
    $items | ForEach-Object {
        @{ PutRequest = @{ Item = $_ } }
    }
)
$requestItems = @{ $tableName = $putRequests }
$temporaryFile = Join-Path ([System.IO.Path]::GetTempPath()) "shifu-dynamodb-batch-write.json"

try {
    $pendingRequests = $requestItems
    do {
        $payload = $pendingRequests | ConvertTo-Json -Depth 20 -Compress
        [System.IO.File]::WriteAllText(
            $temporaryFile,
            $payload,
            [System.Text.UTF8Encoding]::new($false)
        )
        $responseText = & aws dynamodb batch-write-item --request-items "file://$temporaryFile" --region $Region --output json
        if ($LASTEXITCODE -ne 0) {
            throw "AWS CLI nao conseguiu inserir os itens de exemplo no DynamoDB."
        }

        $response = $responseText | ConvertFrom-Json
        $pendingRequests = $response.UnprocessedItems
        if ($pendingRequests -and $pendingRequests.PSObject.Properties.Count -gt 0) {
            Start-Sleep -Seconds 2
        }
    }
    while ($pendingRequests -and $pendingRequests.PSObject.Properties.Count -gt 0)
}
finally {
    Remove-Item -LiteralPath $temporaryFile -Force -ErrorAction SilentlyContinue
}

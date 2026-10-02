param(
    [int]$EventCount = 1000,
    [int]$BatchSize = 25,
    [double]$TargetEventsPerSecond = 50
)

$ErrorActionPreference = "Stop"

if ($EventCount -lt 1) {
    throw "EventCount deve ser maior que zero."
}
if ($BatchSize -lt 1 -or $BatchSize -gt 25) {
    throw "BatchSize deve ficar entre 1 e 25 para batch-write-item."
}

$moduleDirectory = Split-Path -Parent $PSScriptRoot
$region = (& terraform "-chdir=$moduleDirectory" output -raw aws_region).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Nao foi possivel ler o output aws_region do Terraform."
}
$tableName = (& terraform "-chdir=$moduleDirectory" output -raw dynamodb_table_name).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Nao foi possivel ler o output dynamodb_table_name do Terraform."
}

$timestampBase = [DateTime]::UtcNow
$requests = @(
    for ($index = 0; $index -lt $EventCount; $index++) {
        $timestamp = $timestampBase.AddMilliseconds($index).ToString(
            "yyyy-MM-ddTHH:mm:ss.fffZ",
            [Globalization.CultureInfo]::InvariantCulture
        )
        $learnerNumber = ($index % 100) + 1
        $eventTypeNumber = ($index % 4) + 1
        $eventType = "load_test_$eventTypeNumber"
        $eventId = "load-{0:D6}" -f $index

        $item = @{
            user_id     = @{ S = "load-user-{0:D3}" -f $learnerNumber }
            event_key   = @{ S = "$timestamp#$eventId" }
            event_type  = @{ S = $eventType }
            occurred_at = @{ S = $timestamp }
            resource_id = @{ S = "resource-$($index % 20)" }
            session_id  = @{ S = "load-session-$($index % 100)" }
            sequence    = @{ N = "$index" }
        }

        @{ PutRequest = @{ Item = $item } }
    }
)

$temporaryFile = Join-Path ([System.IO.Path]::GetTempPath()) "shifu-dynamodb-load-test.json"
$timer = [System.Diagnostics.Stopwatch]::StartNew()

try {
    for ($offset = 0; $offset -lt $EventCount; $offset += $BatchSize) {
        $lastIndex = [Math]::Min($offset + $BatchSize - 1, $EventCount - 1)
        $batch = @()
        for ($index = $offset; $index -le $lastIndex; $index++) {
            $batch += $requests[$index]
        }

        $pendingRequests = $batch
        $retryCount = 0
        while ($pendingRequests.Count -gt 0) {
            $payload = @{ $tableName = $pendingRequests } | ConvertTo-Json -Depth 20 -Compress
            [System.IO.File]::WriteAllText(
                $temporaryFile,
                $payload,
                [System.Text.UTF8Encoding]::new($false)
            )

            $responseText = & aws dynamodb batch-write-item --request-items "file://$temporaryFile" --region $region --output json
            if ($LASTEXITCODE -ne 0) {
                throw "AWS CLI falhou ao gravar o lote iniciado no evento $offset."
            }

            $response = $responseText | ConvertFrom-Json
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
}
finally {
    $timer.Stop()
    Remove-Item -LiteralPath $temporaryFile -Force -ErrorAction SilentlyContinue
}

$eventsPerSecond = $EventCount / $timer.Elapsed.TotalSeconds
$status = if ($eventsPerSecond -ge $TargetEventsPerSecond) { "PASSOU" } else { "ABAIXO DA META" }

Write-Output "Tabela: $tableName"
Write-Output "Eventos gravados: $EventCount"
Write-Output ("Tempo total: {0:N2} s" -f $timer.Elapsed.TotalSeconds)
Write-Output ("Taxa media: {0:N2} eventos/s" -f $eventsPerSecond)
Write-Output ("Meta academica: {0:N2} eventos/s - {1}" -f $TargetEventsPerSecond, $status)
Write-Output "Registre os valores reais desta execucao; nao os apresente como garantia de desempenho para outros volumes ou regioes."

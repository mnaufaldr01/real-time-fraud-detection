param(
    [int]$TimeoutSeconds = 120
)

$services = @(
    @{ Name = "Zookeeper"; Url = "http://localhost:2181"; Type = "tcp"; Port = 2181 },
    @{ Name = "Kafka"; Url = "localhost:9092"; Type = "tcp"; Port = 9092 },
    @{ Name = "Postgres"; Url = "localhost:5432"; Type = "tcp"; Port = 5432 }
)

function Test-TcpPort {
    param([string]$HostName, [int]$Port)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $client.Connect($HostName, $Port)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

$elapsed = 0
$interval = 3

Write-Host "Waiting for services to become ready (timeout: ${TimeoutSeconds}s)..."

while ($elapsed -lt $TimeoutSeconds) {
    $allReady = $true
    foreach ($svc in $services) {
        $ready = Test-TcpPort -HostName "localhost" -Port $svc.Port
        if (-not $ready) {
            Write-Host "  Waiting for $($svc.Name)..."
            $allReady = $false
        }
    }
    if ($allReady) {
        Write-Host "All core services are ready."
        exit 0
    }
    Start-Sleep -Seconds $interval
    $elapsed += $interval
}

Write-Host "Timeout waiting for services after ${TimeoutSeconds}s"
exit 1

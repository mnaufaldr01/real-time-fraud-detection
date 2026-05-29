# Start React dashboard dev server (requires Node.js 20+ on PATH).
$ErrorActionPreference = "Stop"

function Get-NodeMajor([string]$nodePath) {
    $version = & $nodePath -v
    return [int]($version -replace '^v', '' -split '\.')[0]
}

$candidates = @(
    (Get-Command node -ErrorAction SilentlyContinue).Source,
    "$env:ProgramFiles\nodejs\node.exe",
    "${env:ProgramFiles(x86)}\nodejs\node.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

$nodeExe = $null
foreach ($candidate in $candidates) {
    if ((Get-NodeMajor $candidate) -ge 20) {
        $nodeExe = $candidate
        break
    }
}

if (-not $nodeExe) {
    Write-Host ""
    Write-Host "  Node.js 20+ is required for the React dashboard." -ForegroundColor Red
    Write-Host "  Detected:" -ForegroundColor Yellow
    foreach ($candidate in $candidates) {
        Write-Host "    $candidate -> $(& $candidate -v)"
    }
    Write-Host ""
    Write-Host "  Upgrade (run in an elevated PowerShell if needed):" -ForegroundColor Cyan
    Write-Host "    winget install OpenJS.NodeJS.LTS"
    Write-Host "  Then close and reopen this terminal."
    Write-Host ""
    Write-Host "  Or use Docker instead:" -ForegroundColor Cyan
    Write-Host "    docker compose up -d --build analytics-api dashboard-web"
    Write-Host "    # http://localhost:3000"
    Write-Host ""
    exit 1
}

$nodeDir = Split-Path $nodeExe -Parent
$env:PATH = "$nodeDir;$env:PATH"

Write-Host "Using Node $(& $nodeExe -v) from $nodeExe" -ForegroundColor Green

$repoRoot = Join-Path $PSScriptRoot ".."
$envFile = Join-Path $repoRoot ".env"
$analyticsPort = "8001"
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^\s*ANALYTICS_API_PORT\s*=\s*(\d+)\s*$') {
            $analyticsPort = $Matches[1]
            break
        }
    }
}
$apiUrl = "http://localhost:$analyticsPort/health"
try {
    $null = Invoke-WebRequest -Uri $apiUrl -UseBasicParsing -TimeoutSec 2
    Write-Host "Analytics API reachable at $apiUrl" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "  Analytics API is not running on port $analyticsPort." -ForegroundColor Red
    Write-Host "  Vite proxies /api there — start it in another terminal:" -ForegroundColor Yellow
    Write-Host "    uvicorn analytics_api.main:app --host 0.0.0.0 --port $analyticsPort --reload"
    Write-Host "  Or: docker compose up -d analytics-api"
    Write-Host "  (Ingestion API uses API_PORT=8000 — do not set ANALYTICS_API_PORT to that.)"
    Write-Host "  Mock data only: cd frontend; npm run dev:demo"
    Write-Host ""
}

Set-Location (Join-Path $repoRoot "frontend")
npm run dev

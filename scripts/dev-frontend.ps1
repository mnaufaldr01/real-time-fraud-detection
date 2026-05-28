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
Set-Location (Join-Path $PSScriptRoot "..\frontend")
npm run dev
